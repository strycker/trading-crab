"""Shared test setup: every test gets its own checkout root, runs offline, and the run names its code.

- ``TC_ROOT_DIR`` points at ``tmp_path``, which holds a copy of the repo's config, so no test reads or writes the
  repo's own ``data/`` or ``outputs/``; exported API keys are removed for the test.
- A socket guard makes any network connection fail unless the test is marked ``network``.
- The terminal summary prints the code line (G-16); unlike a report header, it survives ``-q``.
"""

from __future__ import annotations

import shutil
import socket
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def tc_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh checkout root per test: config copied in, no data, no keys."""
    (tmp_path / "config").mkdir()
    shutil.copy(REPO / "config" / "platform_settings.yaml", tmp_path / "config")
    monkeypatch.setenv("TC_ROOT_DIR", str(tmp_path))
    for name in ("FRED_API_KEY", "TIINGO_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


@pytest.fixture(autouse=True)
def _no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly on any socket connection, unless the test is marked ``network``."""
    if request.node.get_closest_marker("network"):
        return

    def guard(*args: object, **kwargs: object) -> None:
        raise RuntimeError("network access in a test: mock the fetch, or mark the test @pytest.mark.network")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    """Name the code under test next to the result line (G-16)."""
    try:
        from trading_crab_lib.platform.code_version import code_version
    except ImportError as exc:
        terminalreporter.write_line(f"Code: unknown (trading_crab_lib does not import: {exc})")
        return
    terminalreporter.write_line(code_version())
