"""Authenticated, loopback-only web GUI for POCArchitect."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Literal, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .config import DEFAULT_MODELS, DEFAULT_PROVIDER, default_output_dir
from .features import read_report_metadata
from .service import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisService,
    AnalysisServiceError,
    PreparedAnalysis,
    provider_configuration,
)

TERMINAL_STATES = {"completed", "failed"}
SESSION_COOKIE = "pocarchitect_gui_session"
PREPARATION_TTL_SECONDS = 30 * 60
JOB_TTL_SECONDS = 24 * 60 * 60
MAX_RETAINED_JOBS = 100
MAX_API_BODY_BYTES = 65_536
MAX_REPORT_PREVIEW_BYTES = 2 * 1024 * 1024
LOGGER = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreparePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_mode: Literal["url", "local"] = "url"
    source: str = Field(default="", max_length=4096)
    provider: Literal["xai", "openai", "groq", "local"] = "xai"
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=0.2, ge=0, le=2)
    base_url: str | None = Field(default=None, max_length=2048)
    output_dir: str | None = Field(default=None, max_length=4096)
    risk_level: str = Field(default="High", max_length=100)
    target_os: str = Field(default="Linux", max_length=200)
    include_mitigations: bool = True
    no_ingest: bool = False
    max_estimated_cost: float | None = Field(default=None, ge=0)
    report_format: Literal["markdown", "html", "pdf", "json"] = "markdown"
    vulnerability_scan: bool = False
    diff_previous: bool = False
    scaffold: bool = False

    def to_request(self) -> AnalysisRequest:
        source = self.source.strip()
        return AnalysisRequest(
            source=source,
            local_path=source if self.source_mode == "local" else None,
            provider=self.provider,
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
            output_dir=self.output_dir,
            risk_level=self.risk_level,
            target_os=self.target_os,
            include_mitigations=self.include_mitigations,
            no_ingest=self.no_ingest,
            max_estimated_cost=self.max_estimated_cost,
            report_format=self.report_format,
            vulnerability_scan=self.vulnerability_scan,
            diff_previous=self.diff_previous,
            scaffold=self.scaffold,
        )


class RunPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preparation_id: str = Field(min_length=10, max_length=128)
    selected_files: list[str] | None = Field(default=None, max_length=25)


class SelectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_files: list[str] | None = Field(default=None, max_length=25)


@dataclass
class GuiJob:
    id: str
    status: str = "queued"
    events: list[dict[str, object]] = field(default_factory=list)
    result: dict[str, object] | None = None
    error: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


class GuiRuntime:
    """In-memory, single-worker job and artifact registry for the local GUI."""

    def __init__(self, service: AnalysisService | None = None) -> None:
        self.service = service or AnalysisService()
        self._prepared: dict[str, PreparedAnalysis] = {}
        self._jobs: dict[str, GuiJob] = {}
        self._artifacts: dict[str, Path] = {}
        self._artifact_ids: dict[Path, str] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="pocarchitect-gui"
        )

    def prepare(self, payload: PreparePayload) -> dict[str, object]:
        events: list[dict[str, object]] = []
        prepared = self.service.prepare(payload.to_request(), events.append)
        with self._lock:
            self._purge_prepared()
            self._purge_jobs()
            self._prepared[prepared.id] = prepared
        view = prepared.public_view()
        view["events"] = events
        view["expires_in_seconds"] = PREPARATION_TTL_SECONDS
        return view

    def estimate(
        self, preparation_id: str, selected_files: list[str] | None
    ) -> dict[str, object]:
        with self._lock:
            self._purge_prepared()
            prepared = self._prepared.get(preparation_id)
        if prepared is None:
            raise AnalysisServiceError(
                "This transfer review is missing, expired, or already used. Prepare it again."
            )
        return self.service.estimate_selection(prepared, selected_files)

    def submit(self, payload: RunPayload) -> GuiJob:
        with self._lock:
            self._purge_prepared()
            self._purge_jobs()
            prepared = self._prepared.pop(payload.preparation_id, None)
            if prepared is None:
                raise AnalysisServiceError(
                    "This transfer review is missing, expired, or already used. Prepare it again."
                )
            job = GuiJob(id=f"run-{uuid_token()}")
            job.events.append(
                {
                    "event": "queued",
                    "message": "Analysis queued.",
                    "at": _now(),
                    "sequence": 0,
                }
            )
            self._jobs[job.id] = job
        self._executor.submit(self._execute, job.id, prepared, payload.selected_files)
        return job

    def _event_sink(self, job_id: str, payload: dict[str, object]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            event = dict(payload)
            event["at"] = _now()
            event["sequence"] = len(job.events)
            job.events.append(event)
            job.updated_at = str(event["at"])

    def _register_artifact(self, path: Path) -> str:
        resolved = path.resolve()
        with self._lock:
            existing = self._artifact_ids.get(resolved)
            if existing is not None:
                return existing
            artifact_id = f"artifact-{uuid_token()}"
            self._artifacts[artifact_id] = resolved
            self._artifact_ids[resolved] = artifact_id
            return artifact_id

    def _purge_prepared(self) -> None:
        current = datetime.now(timezone.utc)
        expired = [
            preparation_id
            for preparation_id, prepared in self._prepared.items()
            if (current - datetime.fromisoformat(prepared.created_at)).total_seconds()
            > PREPARATION_TTL_SECONDS
        ]
        for preparation_id in expired:
            del self._prepared[preparation_id]

    def _purge_jobs(self) -> None:
        current = datetime.now(timezone.utc)
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in TERMINAL_STATES
            and (current - datetime.fromisoformat(job.updated_at)).total_seconds()
            > JOB_TTL_SECONDS
        ]
        for job_id in expired:
            del self._jobs[job_id]
        terminal = sorted(
            (job for job in self._jobs.values() if job.status in TERMINAL_STATES),
            key=lambda job: job.updated_at,
            reverse=True,
        )
        for job in terminal[MAX_RETAINED_JOBS:]:
            self._jobs.pop(job.id, None)

    def _execute(
        self,
        job_id: str,
        prepared: PreparedAnalysis,
        selected_files: list[str] | None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.updated_at = _now()
        try:
            result = self.service.execute(
                prepared, selected_files, lambda event: self._event_sink(job_id, event)
            )
            self._finish(job_id, result)
        except AnalysisServiceError as error:
            self._fail(job_id, str(error))
        except Exception:
            LOGGER.exception("Unexpected GUI analysis failure")
            self._fail(
                job_id, "The analysis failed unexpectedly. Check the terminal log."
            )

    def _finish(self, job_id: str, result: AnalysisResult) -> None:
        with self._lock:
            report_id = self._register_artifact(result.report_path)
            export_id = (
                report_id
                if result.export_path.resolve() == result.report_path.resolve()
                else self._register_artifact(result.export_path)
            )
            job = self._jobs[job_id]
            job.status = "completed"
            job.updated_at = _now()
            job.result = {
                "report_name": result.report_path.name,
                "report_artifact_id": report_id,
                "export_artifact_id": export_id,
                "export_name": result.export_path.name,
                "content": result.content,
                "grounding_files": list(result.grounding_files),
                "estimated_cost_usd": result.estimated_cost_usd,
                "completed_at": result.completed_at,
            }

    def _fail(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.error = message
            job.updated_at = _now()
            self._event_sink(job_id, {"event": "error", "message": message})

    def snapshot(self, job_id: str) -> dict[str, object]:
        with self._lock:
            self._purge_jobs()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return {
                "id": job.id,
                "status": job.status,
                "events": [dict(event) for event in job.events],
                "result": dict(job.result) if job.result is not None else None,
                "error": job.error,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }

    def artifact(self, artifact_id: str) -> Path:
        with self._lock:
            path = self._artifacts.get(artifact_id)
        if path is None or not path.is_file():
            raise KeyError(artifact_id)
        return path

    def reports(self) -> list[dict[str, object]]:
        output = default_output_dir().resolve()
        rows: list[dict[str, object]] = []
        if not output.is_dir():
            return rows
        candidates: list[tuple[float, Path]] = []
        for path in output.glob("POCAnalysis_*.md"):
            try:
                candidates.append((path.stat().st_mtime, path))
            except OSError:
                continue
        for _, path in sorted(candidates, reverse=True)[:40]:
            try:
                metadata = read_report_metadata(path)
                artifact_id = self._register_artifact(path)
                rows.append(
                    {
                        "artifact_id": artifact_id,
                        "name": path.name,
                        "source": metadata.get("source_url", "Unknown source"),
                        "provider": metadata.get("provider", "unknown"),
                        "model": metadata.get("model", "unknown"),
                        "generated_at": metadata.get("generated_at"),
                    }
                )
            except OSError:
                continue
        return rows

    def close(self) -> None:
        with self._lock:
            self._prepared.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)


def uuid_token() -> str:
    return secrets.token_hex(12)


def create_app(
    *,
    session_token: str,
    host: str = "127.0.0.1",
    port: int = 8765,
    runtime: GuiRuntime | None = None,
) -> FastAPI:
    """Create the local app with cookie authentication and strict origin checks."""

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The GUI may bind only to a loopback address")
    if not session_token:
        raise ValueError("A GUI session token is required")

    web_root = Path(str(files("pocarchitect") / "web"))
    runtime_instance = runtime or GuiRuntime()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            runtime_instance.close()

    app = FastAPI(
        title="POCArchitect GUI",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.runtime = runtime_instance
    expected_origins = {
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
        f"http://[::1]:{port}",
    }
    expected_hosts = {"127.0.0.1", "localhost", "::1"}

    def secure_response(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def protect_local_session(request: Request, call_next):
        if request.url.hostname not in expected_hosts or request.url.port != port:
            return secure_response(
                JSONResponse({"detail": "Invalid local host"}, status_code=400)
            )
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                request_size = int(content_length)
            except ValueError:
                return secure_response(
                    JSONResponse({"detail": "Invalid content length"}, status_code=400)
                )
            if request_size > MAX_API_BODY_BYTES:
                return secure_response(
                    JSONResponse({"detail": "Request is too large"}, status_code=413)
                )
        if request.url.path.startswith("/api/"):
            cookie = request.cookies.get(SESSION_COOKIE, "")
            if not hmac.compare_digest(cookie, session_token):
                return secure_response(
                    JSONResponse({"detail": "GUI session required"}, status_code=401)
                )
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin", "")
                if origin not in expected_origins:
                    return secure_response(
                        JSONResponse(
                            {"detail": "Invalid request origin"}, status_code=403
                        )
                    )
                body = await request.body()
                if len(body) > MAX_API_BODY_BYTES:
                    return secure_response(
                        JSONResponse(
                            {"detail": "Request is too large"}, status_code=413
                        )
                    )
        response = await call_next(request)
        return secure_response(response)

    @app.get("/", include_in_schema=False)
    async def index(request: Request):
        supplied = request.query_params.get("token", "")
        if supplied and hmac.compare_digest(supplied, session_token):
            response = RedirectResponse(url="/", status_code=303)
            response.set_cookie(
                SESSION_COOKIE,
                session_token,
                httponly=True,
                samesite="strict",
                max_age=8 * 60 * 60,
                path="/",
            )
            return response
        cookie = request.cookies.get(SESSION_COOKIE, "")
        if not hmac.compare_digest(cookie, session_token):
            raise HTTPException(
                status_code=401, detail="Open the GUI from its launch URL"
            )
        return FileResponse(web_root / "index.html")

    app.mount("/assets", StaticFiles(directory=web_root), name="assets")

    @app.get("/api/bootstrap")
    async def bootstrap() -> dict[str, object]:
        return {
            "version": __version__,
            "default_provider": DEFAULT_PROVIDER,
            "models": DEFAULT_MODELS,
            "providers": provider_configuration(),
            "default_output_dir": str(default_output_dir().resolve()),
            "reports": app.state.runtime.reports(),
            "limits": {
                "preparation_ttl_seconds": PREPARATION_TTL_SECONDS,
                "max_request_bytes": MAX_API_BODY_BYTES,
                "max_files": 25,
            },
        }

    @app.post("/api/preparations")
    async def prepare(payload: PreparePayload) -> dict[str, object]:
        try:
            return await asyncio.to_thread(app.state.runtime.prepare, payload)
        except AnalysisServiceError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/runs", status_code=202)
    async def start_run(payload: RunPayload) -> dict[str, object]:
        try:
            job = app.state.runtime.submit(payload)
        except AnalysisServiceError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"job_id": job.id, "status": job.status}

    @app.post("/api/preparations/{preparation_id}/estimate")
    async def estimate_selection(
        preparation_id: str, payload: SelectionPayload
    ) -> dict[str, object]:
        try:
            return await asyncio.to_thread(
                app.state.runtime.estimate,
                preparation_id,
                payload.selected_files,
            )
        except AnalysisServiceError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/runs/{job_id}")
    async def run_status(job_id: str) -> dict[str, object]:
        try:
            return app.state.runtime.snapshot(job_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404, detail="Analysis run not found"
            ) from error

    @app.get("/api/runs/{job_id}/events")
    async def run_events(job_id: str, request: Request) -> StreamingResponse:
        try:
            app.state.runtime.snapshot(job_id)
        except KeyError as error:
            raise HTTPException(
                status_code=404, detail="Analysis run not found"
            ) from error

        async def stream():
            last_event_id = request.headers.get("last-event-id", "")
            try:
                cursor = max(0, int(last_event_id) + 1)
            except ValueError:
                cursor = 0
            last_status = ""
            heartbeat = 0
            while True:
                if await request.is_disconnected():
                    return
                snapshot = app.state.runtime.snapshot(job_id)
                events = cast(list[dict[str, object]], snapshot["events"])
                for event in events[cursor:]:
                    sequence = int(event.get("sequence", cursor))
                    yield (
                        f"id: {sequence}\n"
                        f"data: {json.dumps({'type': 'event', 'payload': event})}\n\n"
                    )
                cursor = len(events)
                status = str(snapshot["status"])
                if status != last_status:
                    yield f"data: {json.dumps({'type': 'status', 'status': status})}\n\n"
                    last_status = status
                if status in TERMINAL_STATES:
                    yield f"data: {json.dumps({'type': 'finished', 'status': status})}\n\n"
                    return
                heartbeat += 1
                if heartbeat >= 40:
                    yield ": keepalive\n\n"
                    heartbeat = 0
                await asyncio.sleep(0.35)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    @app.get("/api/reports")
    async def reports() -> dict[str, object]:
        return {"reports": app.state.runtime.reports()}

    @app.get("/api/artifacts/{artifact_id}")
    async def artifact_content(artifact_id: str) -> dict[str, object]:
        try:
            path = app.state.runtime.artifact(artifact_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Report not found") from error
        if path.suffix.lower() != ".md":
            raise HTTPException(
                status_code=415, detail="Preview is available for Markdown reports"
            )
        try:
            if path.stat().st_size > MAX_REPORT_PREVIEW_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="This report is too large to preview. Download it instead.",
                )
            text = path.read_text(encoding="utf-8")
        except UnicodeError as error:
            raise HTTPException(
                status_code=415, detail="This report is not valid UTF-8"
            ) from error
        except OSError as error:
            raise HTTPException(
                status_code=404, detail="Report is unavailable"
            ) from error
        if text.startswith("---\n") and "\n---\n" in text[4:]:
            text = text.split("\n---\n", 1)[1].lstrip()
        return {"name": path.name, "content": text}

    @app.get("/api/artifacts/{artifact_id}/download")
    async def artifact_download(artifact_id: str):
        try:
            path = app.state.runtime.artifact(artifact_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Artifact not found") from error
        return FileResponse(
            path, filename=path.name, media_type="application/octet-stream"
        )

    return app
