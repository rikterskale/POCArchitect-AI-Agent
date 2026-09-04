"""Presentation-neutral analysis orchestration for CLI and GUI clients.

The service owns the prepare/approve/execute boundary.  Prepared source content
stays in backend memory; callers receive metadata only and must explicitly
submit the preparation identifier before a provider call can occur.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import typer
from dotenv import dotenv_values, load_dotenv

from .config import (
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_MODELS,
    DEFAULT_PROVIDER,
    DEFAULT_RISK_LEVEL,
    DEFAULT_TARGET_OS,
    DEFAULT_TEMPERATURE,
    MAX_PROMPT_CHARACTERS,
    PROVIDER_KEY_NAMES,
    default_output_dir,
)
from .output import event_payload

EventSink = Callable[[dict[str, object]], None]


class AnalysisServiceError(ValueError):
    """A safe, user-presentable analysis preparation or execution failure."""


@dataclass(frozen=True)
class AnalysisRequest:
    source: str
    provider: str = DEFAULT_PROVIDER
    model: str | None = None
    temperature: float = DEFAULT_TEMPERATURE
    base_url: str | None = None
    output_dir: str | None = None
    local_path: str | None = None
    risk_level: str = DEFAULT_RISK_LEVEL
    target_os: str = DEFAULT_TARGET_OS
    include_mitigations: bool = True
    no_ingest: bool = False
    max_estimated_cost: float | None = None
    report_format: str = "markdown"
    vulnerability_scan: bool = False
    diff_previous: bool = False
    scaffold: bool = False
    run_analyzers: bool = True


@dataclass(frozen=True)
class PreparedAnalysis:
    id: str
    request: AnalysisRequest
    system_prompt: str
    grounding: Any
    redaction_categories: tuple[str, ...]
    redaction_count: int
    character_count: int
    estimated_tokens: int
    estimated_cost_usd: float | None
    created_at: str

    def public_view(self) -> dict[str, object]:
        """Return preparation metadata without source content or credentials."""

        from .features import mock_report

        return {
            "preparation_id": self.id,
            "source": self.request.source,
            "provider": self.request.provider,
            "model": self.request.model,
            "ingestion": self.grounding.ingestion,
            "files": [
                {"path": item.path, "bytes": item.size, "included": True}
                for item in self.grounding.files
            ],
            "total_bytes": sum(item.size for item in self.grounding.files),
            "redaction_categories": list(self.redaction_categories),
            "redaction_count": self.redaction_count,
            "character_count": self.character_count,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "created_at": self.created_at,
            "report_preview": mock_report(
                self.request.source,
                self.request.risk_level,
                self.request.target_os,
                self.request.include_mitigations,
            ),
        }


@dataclass(frozen=True)
class AnalysisResult:
    report_path: Path
    export_path: Path
    content: str
    grounding_files: tuple[str, ...]
    estimated_cost_usd: float | None
    completed_at: str


def _discard_event(_: dict[str, object]) -> None:
    return None


def _emit(sink: EventSink, event: str, message: str, **details: object) -> None:
    sink(event_payload(event, message, **details))


def _build_user_message(
    request: AnalysisRequest,
    grounding: str,
    *,
    plugin_sections: list[str] | None = None,
    vulnerabilities: list[dict[str, Any]] | None = None,
) -> str:
    message = f"""PoC URL: {request.source}

{grounding}

Operator Preferences (respect these exactly):
- Risk Level: {request.risk_level}
- Target OS / Environment: {request.target_os}
- Include Mitigations: {"Yes" if request.include_mitigations else "No"}

Required report feature:
- Include a Mermaid architecture diagram grounded in the selected file structure.
- Include dependency/CVE identifiers only when supported by evidence; label unverified items."""
    if plugin_sections:
        message += "\n\nRegistered analyzer output:\n" + "\n\n".join(plugin_sections)
    if vulnerabilities is not None:
        message += "\n\nVerified OSV dependency records:\n" + json.dumps(
            vulnerabilities, indent=2
        )
    return message


class AnalysisService:
    """Prepare source transfer metadata, then execute only after GUI approval."""

    def normalize_request(self, request: AnalysisRequest) -> AnalysisRequest:
        from .cli import validate_poc_url

        provider = request.provider.strip().lower()
        if provider not in DEFAULT_MODELS:
            raise AnalysisServiceError(f"Unsupported provider: {request.provider}")
        model = (request.model or DEFAULT_MODELS[provider]).strip()
        if not model:
            raise AnalysisServiceError("A model name is required")
        if not 0 <= request.temperature <= 2:
            raise AnalysisServiceError("Temperature must be between 0 and 2")
        if request.max_estimated_cost is not None and request.max_estimated_cost < 0:
            raise AnalysisServiceError("Maximum estimated cost cannot be negative")
        if request.report_format not in {"markdown", "html", "pdf", "json"}:
            raise AnalysisServiceError(
                f"Unsupported report format: {request.report_format}"
            )

        local_path: str | None = None
        source = request.source.strip()
        if request.local_path:
            local = Path(request.local_path).expanduser().resolve()
            if not local.is_dir():
                raise AnalysisServiceError(f"Local source directory not found: {local}")
            local_path = str(local)
            source = str(local)
        elif not source:
            raise AnalysisServiceError("A source URL or local directory is required")
        else:
            try:
                source = validate_poc_url(source, request.no_ingest)
            except ValueError as error:
                raise AnalysisServiceError(f"Invalid source: {error}") from error

        base_url = request.base_url.strip() if request.base_url else None
        if provider == "local":
            base_url = base_url or DEFAULT_LOCAL_BASE_URL
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise AnalysisServiceError(
                    "Local provider endpoint must be a complete http(s) URL"
                )

        output = (
            Path(request.output_dir).expanduser()
            if request.output_dir
            else default_output_dir()
        )
        output = output.resolve()
        return replace(
            request,
            source=source,
            provider=provider,
            model=model,
            base_url=base_url,
            output_dir=str(output),
            local_path=local_path,
            risk_level=request.risk_level.strip() or DEFAULT_RISK_LEVEL,
            target_os=request.target_os.strip() or DEFAULT_TARGET_OS,
        )

    def prepare(
        self, request: AnalysisRequest, event_sink: EventSink = _discard_event
    ) -> PreparedAnalysis:
        from . import cli

        normalized = self.normalize_request(request)
        _emit(
            event_sink,
            "preparation_started",
            "Inspecting source and preparing the transfer review.",
            source=normalized.source,
        )
        try:
            with cli.capture_events(event_sink):
                system_prompt = cli.load_prompt()
                grounding = cli.build_grounding_context(
                    normalized.source,
                    no_ingest=normalized.no_ingest,
                    verbose=False,
                    local_path=(
                        Path(normalized.local_path) if normalized.local_path else None
                    ),
                    curate=False,
                )
        except typer.Exit as error:
            raise AnalysisServiceError(
                f"Preparation failed with exit code {error.exit_code}"
            ) from error
        if grounding.ingestion == "url-only-ingestion-failed":
            raise AnalysisServiceError(
                "Source ingestion failed. Check the source and Git availability, or disable ingestion."
            )

        redacted, categories, redaction_count = cli.redact_sensitive_input(
            grounding.content
        )
        user_message = _build_user_message(normalized, redacted)
        prompt_characters = len(system_prompt) + len(user_message)
        if prompt_characters > MAX_PROMPT_CHARACTERS:
            raise AnalysisServiceError(
                f"Prepared prompt exceeds the safe {MAX_PROMPT_CHARACTERS:,}-character limit"
            )
        estimated_tokens = cli.estimate_input_tokens(system_prompt + user_message)
        estimated_cost = cli.estimate_cost_usd(normalized.model or "", estimated_tokens)
        prepared = PreparedAnalysis(
            id=f"prep-{uuid.uuid4().hex}",
            request=normalized,
            system_prompt=system_prompt,
            grounding=grounding,
            redaction_categories=tuple(categories),
            redaction_count=redaction_count,
            character_count=len(redacted),
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _emit(
            event_sink,
            "preparation_ready",
            "Transfer review is ready. No provider call has been made.",
            preparation_id=prepared.id,
            files=grounding.selected_files,
            redactions=redaction_count,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost,
        )
        return prepared

    def estimate_selection(
        self, prepared: PreparedAnalysis, selected_files: list[str] | None
    ) -> dict[str, object]:
        """Recalculate transfer metadata without exposing or sending content."""

        from . import cli

        grounding = prepared.grounding
        if selected_files is not None:
            try:
                grounding = cli.select_grounding_files(grounding, selected_files)
            except ValueError as error:
                raise AnalysisServiceError(str(error)) from error
        redacted, categories, redaction_count = cli.redact_sensitive_input(
            grounding.content
        )
        user_message = _build_user_message(prepared.request, redacted)
        prompt = prepared.system_prompt + user_message
        if len(prompt) > MAX_PROMPT_CHARACTERS:
            raise AnalysisServiceError(
                f"Selected files exceed the safe {MAX_PROMPT_CHARACTERS:,}-character limit"
            )
        estimated_tokens = cli.estimate_input_tokens(prompt)
        estimated_cost = cli.estimate_cost_usd(
            prepared.request.model or "", estimated_tokens
        )
        cost_limit = prepared.request.max_estimated_cost
        return {
            "files": len(grounding.files),
            "total_bytes": sum(item.size for item in grounding.files),
            "character_count": len(redacted),
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": estimated_cost,
            "redaction_categories": list(categories),
            "redaction_count": redaction_count,
            "within_cost_limit": (
                cost_limit is None
                or estimated_cost is None
                or estimated_cost <= cost_limit
            ),
        }

    def execute(
        self,
        prepared: PreparedAnalysis,
        selected_files: list[str] | None = None,
        event_sink: EventSink = _discard_event,
        *,
        response_override: str | None = None,
    ) -> AnalysisResult:
        from . import cli
        from .features import (
            create_scaffold,
            ensure_architecture_section,
            export_report,
            find_previous_report,
            report_diff,
            run_plugins,
        )
        from .security import extract_dependencies, query_osv

        request = prepared.request
        grounding = prepared.grounding
        if selected_files is not None:
            try:
                grounding = cli.select_grounding_files(grounding, selected_files)
            except ValueError as error:
                raise AnalysisServiceError(str(error)) from error

        redacted, _, _ = cli.redact_sensitive_input(grounding.content)
        plugin_sections = (
            run_plugins(request.source, redacted) if request.run_analyzers else []
        )
        vulnerabilities: list[dict[str, Any]] | None = None
        if request.vulnerability_scan:
            packages = extract_dependencies(redacted)
            try:
                vulnerabilities = query_osv(packages)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                _emit(
                    event_sink,
                    "vulnerability_scan_failed",
                    f"OSV enrichment was unavailable: {cli.friendly_error_message(error)}",
                )
                vulnerabilities = []
            _emit(
                event_sink,
                "vulnerability_scan",
                f"OSV checked {len(packages)} package(s).",
                packages=len(packages),
                vulnerabilities=vulnerabilities,
            )

        user_message = _build_user_message(
            request,
            redacted,
            plugin_sections=plugin_sections,
            vulnerabilities=vulnerabilities,
        )
        total_characters = len(prepared.system_prompt) + len(user_message)
        if total_characters > MAX_PROMPT_CHARACTERS:
            raise AnalysisServiceError(
                f"Selected files exceed the safe {MAX_PROMPT_CHARACTERS:,}-character limit"
            )
        estimated_tokens = cli.estimate_input_tokens(
            prepared.system_prompt + user_message
        )
        estimated_cost = cli.estimate_cost_usd(request.model or "", estimated_tokens)
        if (
            request.max_estimated_cost is not None
            and estimated_cost is not None
            and estimated_cost > request.max_estimated_cost
        ):
            raise AnalysisServiceError(
                f"Estimated input cost ${estimated_cost:.4f} exceeds the configured "
                f"limit ${request.max_estimated_cost:.4f}"
            )

        _emit(
            event_sink,
            "provider_started",
            f"Analyzing with {request.provider}/{request.model}.",
            provider=request.provider,
            model=request.model,
        )
        try:
            with cli.capture_events(event_sink):
                content = (
                    response_override
                    if response_override is not None
                    else cli.get_llm_response(
                        provider=request.provider,
                        api_key=None,
                        model=request.model or "",
                        temperature=request.temperature,
                        base_url=request.base_url,
                        system_prompt=prepared.system_prompt,
                        user_message=user_message,
                    )
                )
        except typer.Exit as error:
            raise AnalysisServiceError(
                f"Provider request failed with exit code {error.exit_code}"
            ) from error
        except Exception as error:
            raise AnalysisServiceError(cli.friendly_error_message(error)) from error

        content = ensure_architecture_section(content, list(grounding.file_names))
        output_dir = Path(request.output_dir or default_output_dir())
        previous = (
            find_previous_report(output_dir, request.source)
            if request.diff_previous
            else None
        )
        _emit(event_sink, "report_writing", "Writing the completed report.")
        try:
            with cli.capture_events(event_sink):
                report_path = cli.save_report(
                    content,
                    request.source,
                    output_dir,
                    request.provider,
                    request.model or "",
                    grounding,
                    risk_level=request.risk_level,
                    target_os=request.target_os,
                )
            export_path = export_report(report_path, request.report_format)
            if export_path != report_path:
                _emit(
                    event_sink,
                    "report_exported",
                    f"Exported {request.report_format} report.",
                    path=str(export_path),
                    format=request.report_format,
                )
            if previous is not None:
                diff_path = report_path.with_suffix(".diff")
                diff_text = report_diff(previous, report_path)
                diff_path.write_text(
                    diff_text + ("\n" if diff_text else "No content changes.\n"),
                    encoding="utf-8",
                )
                _emit(
                    event_sink,
                    "report_diff",
                    "Saved a diff against the previous report.",
                    path=str(diff_path),
                )
            if request.scaffold:
                scaffold_path = output_dir / f"{cli.slugify(request.source)}-blueprint"
                created = create_scaffold(report_path, scaffold_path)
                _emit(
                    event_sink,
                    "scaffold_created",
                    "Created the blueprint scaffold.",
                    path=str(scaffold_path),
                    files=[str(path) for path in created],
                )
        except OSError as error:
            raise AnalysisServiceError(
                f"Could not write the report: {error}"
            ) from error

        _emit(
            event_sink,
            "run_complete",
            "Analysis complete.",
            path=str(report_path),
            estimated_cost_usd=estimated_cost,
        )
        return AnalysisResult(
            report_path=report_path,
            export_path=export_path,
            content=content,
            grounding_files=grounding.file_names,
            estimated_cost_usd=estimated_cost,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )


def provider_configuration() -> dict[str, bool]:
    """Return masked provider readiness for the GUI bootstrap response."""

    from .preflight import _is_valid_key_value

    env_path = Path.cwd() / ".env"
    # Let a running GUI pick up a newly-created credential after the operator
    # returns from the terminal setup wizard. Existing environment variables
    # keep precedence and changed values still require a process restart.
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)
    env_file_values = dotenv_values(env_path) if env_path.is_file() else {}
    return {
        provider: (
            True
            if provider == "local"
            else _is_valid_key_value(os.getenv(environment_name))
            or _is_valid_key_value(env_file_values.get(environment_name))
        )
        for provider, environment_name in {
            **PROVIDER_KEY_NAMES,
            "local": "",
        }.items()
    }
