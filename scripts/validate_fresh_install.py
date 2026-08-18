#!/usr/bin/env python3
"""Install a release artifact in a clean venv and exercise the first-run gate."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS_GATE = ROOT / "scripts" / "release_readiness.py"
ARTIFACT_PATTERNS = {
    "wheel": "*.whl",
    "sdist": "*.tar.gz",
}


def select_artifact(dist: Path, artifact_kind: str) -> Path:
    matches = sorted(dist.glob(ARTIFACT_PATTERNS[artifact_kind]))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one {artifact_kind} in {dist}; found {len(matches)}."
        )
    return matches[0].resolve()


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def clean_environment() -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "XAI_API_KEY",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "IN_DOCKER",
        "PYTHONPATH",
        "PYTHONHOME",
    ):
        env.pop(key, None)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument(
        "--artifact",
        choices=sorted(ARTIFACT_PATTERNS),
        default="wheel",
    )
    args = parser.parse_args()

    try:
        artifact = select_artifact(args.dist, args.artifact)
    except ValueError as error:
        parser.error(str(error))

    env = clean_environment()
    with tempfile.TemporaryDirectory() as temporary:
        scratch = Path(temporary)
        venv_dir = scratch / "venv"
        work_dir = scratch / "first-run"
        work_dir.mkdir()

        run([sys.executable, "-m", "venv", str(venv_dir)], cwd=scratch, env=env)
        python = venv_python(venv_dir)
        run(
            [str(python), "-m", "pip", "install", str(artifact)],
            cwd=work_dir,
            env=env,
        )
        run([str(python), "-m", "pip", "check"], cwd=work_dir, env=env)

        probe = (
            "from pathlib import Path; import pocarchitect; "
            "print(Path(pocarchitect.__file__).resolve())"
        )
        run([str(python), "-c", probe], cwd=work_dir, env=env)
        run(
            [
                str(python),
                str(READINESS_GATE),
                "--format",
                "text",
                "--require-console-script",
            ],
            cwd=work_dir,
            env=env,
        )

    print(f"Clean {args.artifact} install passed the first-run readiness gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
