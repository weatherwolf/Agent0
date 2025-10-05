# core/execution.py
import subprocess
from typing import List, Tuple

def is_prefix(cmd: List[str], prefix: Tuple[str, ...]) -> bool:
    return tuple(cmd[:len(prefix)]) == prefix

def allow_exec(cmd: List[str], workspace_path: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """
    Minimal allowlist for subprocess. Extend when needed.
    """
    allowed_prefixes = [
        ("pytest", "-q"),
        ("pytest",),
        ("python", "-m", "pip", "install"),
        ("python", "-c"),  # Allow python -c commands for import testing
    ]
    if not any(is_prefix(cmd, p) for p in allowed_prefixes):
        raise RuntimeError(f"Blocked command: {cmd}")

    return subprocess.run(
        cmd,
        cwd=workspace_path,
        capture_output=True,
        text=True,
        timeout=timeout
    )
