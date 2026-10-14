"""Which code is running, as the first line of every command and test run (G-16).

Usage::

    from trading_crab_lib.platform.code_version import code_version
    print(code_version())   # Code: claude/phase-9.1-skeleton @ 1ca9d42 — /Users/me/trading-crab

Git runs in this file's own folder, so the line names the checkout whose code executes (an editable install of
another clone shows up here), not the shell's working directory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _git(*args: str, cwd: Path | None = None) -> str | None:
    """Stdout of a git command, or None when git is missing, hangs or fails."""
    try:
        done = subprocess.run(["git", *args], cwd=cwd or _HERE, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def code_version() -> str:
    """``Code: <branch> @ <short sha>[ + uncommitted changes] — <checkout>``; a detached HEAD reads ``(detached)``."""
    sha = _git("rev-parse", "--short", "HEAD")
    if sha is None:
        return f"Code: not a git checkout (or git unavailable) — {_HERE}"
    root = _git("rev-parse", "--show-toplevel")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = "(detached)" if branch in (None, "HEAD") else branch
    status = _git("status", "--porcelain", "--", "src", "scripts", "config", cwd=Path(root) if root else None)
    dirty = " (uncommitted changes unknown)" if status is None else (" + uncommitted changes" if status else "")
    return f"Code: {branch} @ {sha}{dirty} — {root or _HERE}"
