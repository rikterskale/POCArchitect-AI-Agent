"""Contract-driven PoC build and test verification in a constrained container."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat

# Docker CLI execution is the documented verification boundary.
import subprocess  # nosec B404
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Sequence, cast

from .file_io import harden_private_descriptor, harden_private_path

CONTRACT_FILENAME = "poc-verification.json"
CONTRACT_SCHEMA_VERSION = 1
EVIDENCE_SCHEMA_VERSION = 1
DEFAULT_IMAGE = "python:3.12-slim"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_COMMAND_LENGTH = 4096
MAX_LOG_BYTES = 64 * 1024
MAX_SOURCE_FILES = 25_000
MAX_SOURCE_BYTES = 512 * 1024 * 1024
_IMAGE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:@-]{0,254}\Z")
_ARTIFACT_PATTERN = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._/-]{0,239}\Z")
_IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
}


class VerificationError(RuntimeError):
    """Base error for verification configuration and runtime failures."""


class ContractError(VerificationError):
    """The explicit verification contract is invalid or incomplete."""


class RuntimeUnavailableError(VerificationError):
    """The local Docker verification boundary is unavailable."""


@dataclass(frozen=True)
class VerificationContract:
    """Validated commands and runtime settings for one PoC implementation."""

    project_name: str
    authorization: str
    image: str
    build_commands: tuple[str, ...]
    test_commands: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    implementation_status: str


@dataclass(frozen=True)
class StepResult:
    """One preparation, build, test, artifact, or cleanup result."""

    name: str
    command: str
    exit_code: int | None
    duration_seconds: float
    passed: bool
    timed_out: bool
    stdout: str
    stderr: str


@dataclass(frozen=True)
class VerificationResult:
    """Durable result for a completed verification attempt."""

    verification_id: str
    status: str
    started_at: str
    finished_at: str
    project_name: str
    authorization: str
    source_sha256: str
    contract_sha256: str
    image: str
    image_id: str
    evidence_path: Path
    sandbox: dict[str, object]
    excluded_paths: tuple[str, ...]
    steps: tuple[StepResult, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the stable evidence document shape."""
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "verification_id": self.verification_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "project_name": self.project_name,
            "authorization": self.authorization,
            "source_sha256": self.source_sha256,
            "contract_sha256": self.contract_sha256,
            "image": self.image,
            "image_id": self.image_id,
            "sandbox": self.sandbox,
            "excluded_paths": list(self.excluded_paths),
            "steps": [asdict(step) for step in self.steps],
        }


def utc_now() -> str:
    """Return a compact, timezone-aware evidence timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_evidence_path(project: Path) -> Path:
    """Return a collision-resistant default path outside the source project."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        Path("reports")
        / f"verification-{project.name}-{stamp}-{uuid.uuid4().hex[:8]}.json"
    )


def _absolute_without_resolving(path: Path) -> Path:
    """Make a path absolute while preserving a final symlink for safe replacement."""
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _is_ignored(directory: Path, name: str) -> bool:
    if name in _IGNORED_DIRECTORIES:
        return True
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    return directory.name == ".pocarchitect" and name == "verification"


def _scan_source(project: Path) -> tuple[int, int, tuple[str, ...]]:
    file_count = 0
    byte_count = 0
    excluded: list[str] = []
    for root, directories, files in os.walk(project, topdown=True, followlinks=False):
        root_path = Path(root)
        kept_directories = []
        for name in sorted(directories):
            relative = (root_path / name).relative_to(project).as_posix()
            if _is_ignored(root_path, name):
                excluded.append(relative)
            else:
                kept_directories.append(name)
        directories[:] = kept_directories
        for name in sorted(files):
            path = root_path / name
            relative = path.relative_to(project).as_posix()
            if _is_ignored(root_path, name):
                excluded.append(relative)
                continue
            try:
                metadata = path.lstat()
            except OSError as error:
                raise VerificationError(
                    f"Cannot inspect source path {relative}: {error}"
                ) from error
            if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)):
                excluded.append(relative)
                continue
            file_count += 1
            byte_count += metadata.st_size
            if file_count > MAX_SOURCE_FILES:
                raise VerificationError(
                    f"Source snapshot exceeds the {MAX_SOURCE_FILES:,}-file safety limit."
                )
            if byte_count > MAX_SOURCE_BYTES:
                raise VerificationError(
                    "Source snapshot exceeds the 512 MiB safety limit."
                )
    return file_count, byte_count, tuple(sorted(excluded))


def _copy_snapshot(project: Path, destination: Path) -> tuple[str, tuple[str, ...]]:
    _, _, excluded = _scan_source(project)

    def ignore(directory: str, names: list[str]) -> list[str]:
        parent = Path(directory)
        ignored: list[str] = []
        for name in names:
            path = parent / name
            if _is_ignored(parent, name):
                ignored.append(name)
                continue
            try:
                mode = path.lstat().st_mode
            except OSError as error:
                raise VerificationError(
                    f"Cannot inspect source path {path}: {error}"
                ) from error
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
                ignored.append(name)
        return ignored

    shutil.copytree(project, destination, symlinks=True, ignore=ignore)
    # Scaffold artifacts are owner-only on the host. The snapshot lives beneath
    # a private temporary parent, so normalize only this disposable copy for the
    # non-root container user and preserve whether regular files are executable.
    destination.chmod(0o755)
    for path in sorted(destination.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            executable = bool(stat.S_IMODE(path.stat().st_mode) & 0o111)
            path.chmod(0o755 if executable else 0o644)

    digest = hashlib.sha256()
    for path in sorted(destination.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(destination).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            digest.update(b"L\0" + relative.encode() + b"\0")
            digest.update(os.readlink(path).encode(errors="surrogateescape") + b"\0")
        elif path.is_dir():
            digest.update(b"D\0" + relative.encode() + b"\0")
            digest.update(f"{mode:o}".encode() + b"\0")
        elif path.is_file():
            digest.update(b"F\0" + relative.encode() + b"\0")
            digest.update(f"{mode:o}".encode() + b"\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")
    return digest.hexdigest(), excluded


def _validate_commands(value: object, field: str, *, required: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractError(f"{field} must be a JSON array of command strings.")
    commands = tuple(item.strip() for item in value)
    if required and not commands:
        raise ContractError(f"{field} must contain at least one explicit command.")
    for command in commands:
        if not command:
            raise ContractError(f"{field} cannot contain an empty command.")
        if "\x00" in command or len(command) > MAX_COMMAND_LENGTH:
            raise ContractError(
                f"Each {field} entry must be at most {MAX_COMMAND_LENGTH} characters and contain no NUL byte."
            )
    return commands


def _validate_artifacts(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractError(
            "required_artifacts must be a JSON array of relative paths."
        )
    artifacts: list[str] = []
    for item in value:
        candidate = Path(item)
        if (
            not item
            or candidate.is_absolute()
            or not candidate.parts
            or ".." in candidate.parts
            or "\\" in item
            or re.match(r"^[A-Za-z]:", item)
            or "\x00" in item
            or not _ARTIFACT_PATTERN.fullmatch(item)
            or candidate.as_posix() != item
        ):
            raise ContractError(
                "required_artifacts entries must be non-empty paths contained by the project."
            )
        normalized = candidate.as_posix()
        if normalized in artifacts:
            raise ContractError("required_artifacts cannot contain duplicate paths.")
        artifacts.append(normalized)
    return tuple(artifacts)


def _validate_contract_document(
    document: object, *, require_ready: bool
) -> VerificationContract:
    """Validate a decoded contract before it can be written or executed."""
    if not isinstance(document, dict):
        raise ContractError("Verification contract must contain one JSON object.")
    expected_fields = {
        "schema_version",
        "project_name",
        "authorization",
        "implementation_status",
        "image",
        "build_commands",
        "test_commands",
        "required_artifacts",
    }
    unexpected = sorted(set(document) - expected_fields)
    if unexpected:
        raise ContractError(
            "Verification contract contains unsupported fields: "
            + ", ".join(unexpected)
        )
    if document.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise ContractError(
            f"Verification contract schema_version must be {CONTRACT_SCHEMA_VERSION}."
        )
    project_name = document.get("project_name")
    authorization = document.get("authorization")
    image = document.get("image")
    status = document.get("implementation_status")
    if not isinstance(project_name, str) or not project_name.strip():
        raise ContractError("project_name must be a non-empty string.")
    if not isinstance(authorization, str):
        raise ContractError(
            "authorization must be a string describing the approved lab scope."
        )
    if not isinstance(image, str) or not _IMAGE_PATTERN.fullmatch(image):
        raise ContractError("image must be a valid Docker image reference.")
    if status not in {"draft", "ready"}:
        raise ContractError("implementation_status must be 'draft' or 'ready'.")
    if require_ready and status != "ready":
        raise ContractError(
            "Implementation is still draft. Review it, add meaningful tests, then set implementation_status to 'ready'."
        )
    if require_ready and not authorization.strip():
        raise ContractError(
            "authorization must describe the approved lab scope before verification."
        )
    return VerificationContract(
        project_name=project_name.strip(),
        authorization=authorization.strip(),
        image=image,
        build_commands=_validate_commands(
            document.get("build_commands", []), "build_commands", required=False
        ),
        test_commands=_validate_commands(
            document.get("test_commands", []), "test_commands", required=True
        ),
        required_artifacts=_validate_artifacts(document.get("required_artifacts", [])),
        implementation_status=status,
    )


def load_contract(path: Path, *, require_ready: bool = True) -> VerificationContract:
    """Load and strictly validate a verification contract."""
    try:
        document = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(
            f"Cannot read verification contract {path}: {error}"
        ) from error
    return _validate_contract_document(document, require_ready=require_ready)


def _detected_commands(project: Path) -> tuple[str, list[str], list[str]]:
    if (
        (project / "pyproject.toml").exists()
        or (project / "setup.py").exists()
        or any(project.rglob("*.py"))
    ):
        return (
            DEFAULT_IMAGE,
            ["python -m compileall -q ."],
            ["python -m unittest discover -s tests -v"],
        )
    if (project / "package.json").exists():
        return "node:22-slim", ["npm run build --if-present"], ["npm test"]
    if any(project.rglob("*.js")):
        return (
            "node:22-slim",
            ["node --check $(find . -name '*.js' -type f)"],
            ["node --test"],
        )
    if (project / "Cargo.toml").exists():
        return "rust:1.85-slim", ["cargo check --locked"], ["cargo test --locked"]
    if (project / "go.mod").exists():
        return "golang:1.24", ["go build ./..."], ["go test ./..."]
    if (project / "Makefile").exists() or (project / "makefile").exists():
        return "debian:bookworm-slim", ["make"], ["make test"]
    raise ContractError(
        "Could not infer build and test commands. Supply --image and at least one --test-command."
    )


def create_contract(
    project: Path,
    destination: Path,
    *,
    image: str | None = None,
    build_commands: Sequence[str] = (),
    test_commands: Sequence[str] = (),
    required_artifacts: Sequence[str] = (),
    authorization: str = "",
    ready: bool = False,
    force: bool = False,
) -> Path:
    """Create an inspectable verification contract without executing code."""
    project = project.resolve()
    if not project.is_dir():
        raise ContractError(f"Project directory does not exist: {project}")
    detected_image: str
    detected_build: list[str]
    detected_test: list[str]
    if image is not None and test_commands:
        detected_image, detected_build, detected_test = image, [], list(test_commands)
    else:
        detected_image, detected_build, detected_test = _detected_commands(project)
    selected_image = image or detected_image
    document = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "project_name": project.name,
        "authorization": authorization.strip(),
        "implementation_status": "ready" if ready else "draft",
        "image": selected_image,
        "build_commands": list(build_commands) or detected_build,
        "test_commands": list(test_commands) or detected_test,
        "required_artifacts": list(required_artifacts),
    }
    # A ready contract must already include its authorization gate; drafts may be
    # incomplete because they cannot be executed.
    _validate_contract_document(document, require_ready=ready)
    if ready and not test_commands:
        raise ContractError(
            "Creating a ready contract requires at least one explicit test command. "
            "Pass --test-command or create a draft and review its inferred command."
        )
    temporary_document = json.dumps(document, indent=2, sort_keys=True) + "\n"
    destination = _absolute_without_resolving(destination)
    if (destination.exists() or destination.is_symlink()) and not force:
        raise ContractError(
            f"Contract already exists: {destination}. Use --force to replace it."
        )
    _write_private_text(destination, temporary_document)
    return destination


def _truncate(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = value
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_LOG_BYTES:
        return text
    suffix = b"\n[output truncated by POCArchitect]\n"
    prefix_limit = MAX_LOG_BYTES - len(suffix)
    prefix = encoded[:prefix_limit].decode("utf-8", errors="ignore")
    return prefix + suffix.decode("utf-8")


def _run_host(
    arguments: Sequence[str], *, timeout: int
) -> subprocess.CompletedProcess[str]:
    """Run a Docker CLI operation without invoking a host shell."""
    # Arguments target the fixed Docker boundary and never invoke a host shell.
    return subprocess.run(  # nosec B603
        list(arguments),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )


def _run_host_bounded(
    arguments: Sequence[str], *, timeout: int
) -> tuple[subprocess.CompletedProcess[str], bool]:
    """Run an untrusted-output Docker operation with bounded host memory."""
    # Arguments target the fixed Docker boundary and never invoke a host shell.
    process = subprocess.Popen(  # nosec B603
        list(arguments),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout_stream = cast(BinaryIO, process.stdout)
    stderr_stream = cast(BinaryIO, process.stderr)
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    stdout_truncated = threading.Event()
    stderr_truncated = threading.Event()

    def drain(stream: BinaryIO, buffer: bytearray, truncated: threading.Event) -> None:
        try:
            while chunk := stream.read(8192):
                available = MAX_LOG_BYTES - len(buffer)
                if available > 0:
                    buffer.extend(chunk[:available])
                if len(chunk) > available:
                    truncated.set()
        except (OSError, ValueError):
            truncated.set()

    stdout_thread = threading.Thread(
        target=drain,
        args=(stdout_stream, stdout_buffer, stdout_truncated),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=drain,
        args=(stderr_stream, stderr_buffer, stderr_truncated),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        returncode = process.wait()
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    for stream, thread in (
        (stdout_stream, stdout_thread),
        (stderr_stream, stderr_thread),
    ):
        if thread.is_alive():
            stream.close()
            thread.join(timeout=1)

    def decoded(buffer: bytearray, truncated: threading.Event) -> str:
        suffix = b"\n[output truncated by POCArchitect]\n"
        content = bytes(buffer)
        if truncated.is_set():
            content = content[: MAX_LOG_BYTES - len(suffix)] + suffix
        return _truncate(content.decode("utf-8", errors="replace"))

    return (
        subprocess.CompletedProcess(
            list(arguments),
            returncode,
            decoded(stdout_buffer, stdout_truncated),
            decoded(stderr_buffer, stderr_truncated),
        ),
        timed_out,
    )


def _require_runtime(image: str) -> str:
    if shutil.which("docker") is None:
        raise RuntimeUnavailableError(
            "Docker was not found. Install and start Docker before verification."
        )
    try:
        info = _run_host(
            ["docker", "info", "--format", "{{.ServerVersion}}"], timeout=15
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeUnavailableError(
            f"Docker did not respond to the runtime check: {error}"
        ) from error
    if info.returncode != 0:
        raise RuntimeUnavailableError(
            "Docker is installed but unavailable: "
            + _truncate(info.stderr or info.stdout).strip()
        )
    try:
        inspected = _run_host(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeUnavailableError(
            f"Docker could not inspect the verification image: {error}"
        ) from error
    if inspected.returncode != 0:
        raise RuntimeUnavailableError(
            f"Verification image is not available locally: {image}. Review it, then run: docker pull {image}"
        )
    image_id = inspected.stdout.strip()
    if not image_id:
        raise RuntimeUnavailableError(f"Docker returned no image ID for {image}.")
    return image_id


def _sandbox_arguments(
    *, container_name: str, verification_id: str, snapshot: Path, image: str
) -> list[str]:
    if "," in str(snapshot):
        raise VerificationError("Verification snapshot path cannot contain a comma.")
    # This is a container-internal tmpfs target, not a host temporary path.
    container_temporary_directory = "/" + "tmp"
    return [
        "docker",
        "run",
        "--detach",
        "--name",
        container_name,
        "--label",
        f"com.pocarchitect.verification={verification_id}",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--memory=512m",
        "--cpus=1.0",
        "--user=65534:65534",
        "--tmpfs",
        "/workspace:rw,nosuid,nodev,size=512m,uid=65534,gid=65534,mode=0700",
        "--tmpfs",
        f"{container_temporary_directory}:rw,nosuid,nodev,size=128m,uid=65534,gid=65534,mode=1777",
        "--mount",
        f"type=bind,source={snapshot},target=/source,readonly",
        "--workdir=/workspace",
        "--entrypoint=/bin/sh",
        image,
        "-c",
        "while :; do sleep 3600; done",
    ]


def _execute_step(
    container_name: str, name: str, command: str, timeout: int
) -> StepResult:
    started = time.monotonic()
    arguments = [
        "docker",
        "exec",
        "--workdir=/workspace",
        container_name,
        "/bin/sh",
        "-lc",
        command,
    ]
    try:
        completed, timed_out = _run_host_bounded(arguments, timeout=timeout)
    except OSError as error:
        return StepResult(
            name=name,
            command=command,
            exit_code=None,
            duration_seconds=round(time.monotonic() - started, 3),
            passed=False,
            timed_out=False,
            stdout="",
            stderr=_truncate(str(error)),
        )
    return StepResult(
        name=name,
        command=command,
        exit_code=None if timed_out else completed.returncode,
        duration_seconds=round(time.monotonic() - started, 3),
        passed=not timed_out and completed.returncode == 0,
        timed_out=timed_out,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _execute_artifact_check(
    container_name: str, artifact: str, timeout: int
) -> StepResult:
    started = time.monotonic()
    arguments = [
        "docker",
        "exec",
        container_name,
        "/bin/sh",
        "-c",
        'test -e "$1" && test ! -L "$1"',
        "pocarchitect-artifact-check",
        f"/workspace/{artifact}",
    ]
    try:
        completed = _run_host(arguments, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        return StepResult(
            name=f"artifact:{artifact}",
            command=f"test -e {artifact}",
            exit_code=None,
            duration_seconds=round(time.monotonic() - started, 3),
            passed=False,
            timed_out=isinstance(error, subprocess.TimeoutExpired),
            stdout=_truncate(getattr(error, "stdout", None)),
            stderr=_truncate(getattr(error, "stderr", None) or str(error)),
        )
    return StepResult(
        name=f"artifact:{artifact}",
        command=f"test -e {artifact}",
        exit_code=completed.returncode,
        duration_seconds=round(time.monotonic() - started, 3),
        passed=completed.returncode == 0,
        timed_out=False,
        stdout=_truncate(completed.stdout),
        stderr=_truncate(completed.stderr),
    )


def _cleanup_container(container_name: str) -> StepResult:
    """Force-remove the sandbox and retain cleanup as part of the evidence."""
    started = time.monotonic()
    arguments = ["docker", "rm", "--force", container_name]
    try:
        completed = _run_host(arguments, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return StepResult(
            name="cleanup",
            command="docker rm --force <verification-container>",
            exit_code=None,
            duration_seconds=round(time.monotonic() - started, 3),
            passed=False,
            timed_out=isinstance(error, subprocess.TimeoutExpired),
            stdout=_truncate(getattr(error, "stdout", None)),
            stderr=_truncate(getattr(error, "stderr", None) or str(error)),
        )
    return StepResult(
        name="cleanup",
        command="docker rm --force <verification-container>",
        exit_code=completed.returncode,
        duration_seconds=round(time.monotonic() - started, 3),
        passed=completed.returncode == 0,
        timed_out=False,
        stdout=_truncate(completed.stdout),
        stderr=_truncate(completed.stderr),
    )


def _write_private_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        harden_private_descriptor(descriptor)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        harden_private_path(path)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def run_verification(
    project: Path,
    contract_path: Path,
    evidence_path: Path,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> VerificationResult:
    """Build and test one ready implementation inside the locked-down sandbox."""
    if timeout_seconds < 1 or timeout_seconds > 3600:
        raise VerificationError("timeout_seconds must be between 1 and 3600.")
    project = project.resolve()
    if not project.is_dir():
        raise VerificationError(f"Project directory does not exist: {project}")
    contract_path = contract_path.resolve()
    contract = load_contract(contract_path)
    evidence_path = _absolute_without_resolving(evidence_path)
    if evidence_path.exists() or evidence_path.is_symlink():
        raise VerificationError(
            f"Evidence path already exists; choose a new path: {evidence_path}"
        )
    contract_sha256 = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    image_id = _require_runtime(contract.image)
    verification_id = uuid.uuid4().hex
    container_name = f"pocarchitect-verify-{verification_id[:12]}"
    started_at = utc_now()
    steps: list[StepResult] = []

    with tempfile.TemporaryDirectory(prefix="pocarchitect-verification-") as directory:
        snapshot = Path(directory) / "source"
        try:
            source_sha256, excluded = _copy_snapshot(project, snapshot)
        except (OSError, shutil.Error) as error:
            raise VerificationError(
                f"Could not create the isolated source snapshot: {error}"
            ) from error
        try:
            started_container = _run_host(
                _sandbox_arguments(
                    container_name=container_name,
                    verification_id=verification_id,
                    snapshot=snapshot,
                    image=contract.image,
                ),
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            _cleanup_container(container_name)
            raise RuntimeUnavailableError(
                f"Could not start verification sandbox: {error}"
            ) from error
        if started_container.returncode != 0:
            # Docker can leave a named container behind when startup fails after
            # creation. Best-effort removal prevents an orphaned sandbox.
            _cleanup_container(container_name)
            raise RuntimeUnavailableError(
                "Could not start verification sandbox: "
                + _truncate(
                    started_container.stderr or started_container.stdout
                ).strip()
            )
        try:
            prepared = _execute_step(
                container_name,
                "prepare",
                "cp -R /source/. /workspace/",
                min(timeout_seconds, 120),
            )
            steps.append(prepared)
            if prepared.passed:
                for index, command in enumerate(contract.build_commands, 1):
                    step = _execute_step(
                        container_name, f"build:{index}", command, timeout_seconds
                    )
                    steps.append(step)
                    if not step.passed:
                        break
            if all(step.passed for step in steps):
                for index, command in enumerate(contract.test_commands, 1):
                    step = _execute_step(
                        container_name, f"test:{index}", command, timeout_seconds
                    )
                    steps.append(step)
                    if not step.passed:
                        break
            if all(step.passed for step in steps):
                for artifact in contract.required_artifacts:
                    step = _execute_artifact_check(
                        container_name, artifact, min(timeout_seconds, 30)
                    )
                    steps.append(step)
                    if not step.passed:
                        break
        finally:
            steps.append(_cleanup_container(container_name))

    status = "verified" if steps and all(step.passed for step in steps) else "failed"
    result = VerificationResult(
        verification_id=verification_id,
        status=status,
        started_at=started_at,
        finished_at=utc_now(),
        project_name=contract.project_name,
        authorization=contract.authorization,
        source_sha256=source_sha256,
        contract_sha256=contract_sha256,
        image=contract.image,
        image_id=image_id,
        evidence_path=evidence_path,
        sandbox={
            "runtime": "docker",
            "network": "none",
            "read_only_root": True,
            "read_only_source_snapshot": True,
            "capabilities_dropped": ["ALL"],
            "no_new_privileges": True,
            "runtime_user": "65534:65534",
            "pids_limit": 128,
            "memory_limit": "512m",
            "cpu_limit": 1.0,
            "command_timeout_seconds": timeout_seconds,
            "implicit_image_pull": False,
        },
        excluded_paths=excluded,
        steps=tuple(steps),
    )
    _write_private_text(
        result.evidence_path,
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
    )
    return result
