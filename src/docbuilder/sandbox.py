"""Constrained execution for the LaTeX build path.

LaTeX is compiled from text derived from untrusted ``.docx`` uploads, so the build
runs under tight limits. Two backends:

* ``local``  — a hardened subprocess: POSIX resource limits (CPU/memory/output
  size), a wall-clock timeout that kills the whole process group, and a
  sanitized environment that disables ``\\write18`` shell-escape and restricts
  TeX file reads/writes to the working tree (blocks ``\\input{/etc/passwd}`` and
  writes outside the workspace).
* ``docker`` — runs the same command inside a throwaway, network-less container
  with CPU/memory/PID caps. Strongest isolation; requires Docker on the host.

Selected via ``LATEX_SANDBOX`` (see :mod:`docbuilder.config`).
"""

from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import (
    LATEX_BUILD_TIMEOUT,
    LATEX_CPU_SECONDS,
    LATEX_DOCKER_IMAGE,
    LATEX_MAX_MEMORY_MB,
    LATEX_MAX_OUTPUT_MB,
    LATEX_SANDBOX,
)

try:  # POSIX-only; the local backend degrades gracefully without it.
    import resource
except ImportError:  # pragma: no cover - non-POSIX
    resource = None  # type: ignore[assignment]


@dataclass
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def hardened_tex_env(workspace: Path) -> dict[str, str]:
    """A minimal environment that locks down TeX's dangerous features.

    ``openin_any=p`` / ``openout_any=p`` restrict file IO to the current tree;
    ``shell_escape=f`` disables ``\\write18``. These are kpathsea variables and
    override ``texmf.cnf`` when set in the environment.
    """
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(workspace),
        "TMPDIR": str(workspace),
        "TEXMFVAR": str(workspace / ".texmf-var"),
        "TEXMFHOME": str(workspace / ".texmf-home"),
        "openin_any": "p",        # paranoid: no reads outside the tree
        "openout_any": "p",       # paranoid: no writes outside the tree
        "shell_escape": "f",      # disable \write18 shell-escape
        "max_print_line": "1000",
        "SOURCE_DATE_EPOCH": "0",  # reproducible builds
        # Pass the auto-install flag through so build scripts can honor it.
        "LATEX_AUTO_INSTALL": os.environ.get("LATEX_AUTO_INSTALL", "0"),
    }


def _apply_rlimits() -> None:  # pragma: no cover - runs in the child process
    if resource is None:
        return
    cpu = LATEX_CPU_SECONDS
    mem = LATEX_MAX_MEMORY_MB * 1024 * 1024
    fsize = LATEX_MAX_OUTPUT_MB * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    except (ValueError, OSError):
        pass  # some platforms reject RLIMIT_AS for the address space requested
    os.setsid()  # own process group, so a timeout can kill the whole tree


def _run_local(cmd: list[str], cwd: Path, workspace: Path, timeout: int) -> SandboxResult:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=hardened_tex_env(workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=_apply_rlimits if os.name == "posix" else None,
        )
        return SandboxResult(proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        return SandboxResult(
            returncode=124,
            stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=(exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
            + f"\n[sandbox] build exceeded {timeout}s and was terminated.",
            timed_out=True,
        )


def _run_docker(cmd: list[str], workspace: Path, timeout: int) -> SandboxResult:
    """Run the build command inside a network-less, resource-capped container.

    The command is executed with the workspace mounted at /work; build scripts
    receive that as their source path. Requires Docker on the host.
    """
    docker_cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--memory", f"{LATEX_MAX_MEMORY_MB}m",
        "--cpus", "1",
        "--pids-limit", "256",
        "--security-opt", "no-new-privileges",
        "--read-only",
        "--tmpfs", "/tmp:exec",
        "-v", f"{workspace}:/work:rw",
        "-w", "/work",
        "-e", "openin_any=p", "-e", "openout_any=p", "-e", "shell_escape=f",
        LATEX_DOCKER_IMAGE,
        *cmd,
    ]
    try:
        proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
        return SandboxResult(proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        return SandboxResult(124, "", f"[sandbox] docker build exceeded {timeout}s.", timed_out=True)


def run_sandboxed(
    cmd: list[str],
    *,
    cwd: Path,
    workspace: Path,
    timeout: int | None = None,
    docker_cmd: list[str] | None = None,
) -> SandboxResult:
    """Run ``cmd`` under the configured sandbox.

    ``cmd`` is the local-backend command (e.g. ``["bash", build_sh, workspace]``).
    ``docker_cmd`` is the equivalent command relative to the container mount
    (``/work``); if omitted, the docker backend reuses ``cmd``.
    """
    timeout = timeout or LATEX_BUILD_TIMEOUT
    if LATEX_SANDBOX == "docker":
        return _run_docker(docker_cmd or cmd, workspace, timeout)
    return _run_local(cmd, cwd, workspace, timeout)
