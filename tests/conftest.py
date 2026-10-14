"""Shared test setup: every test gets its own checkout root, runs offline, and the run names its code.

- ``TC_ROOT_DIR`` points at ``tmp_path``, which holds a copy of the repo's config, so no test reads or writes the
  repo's own ``data/`` or ``outputs/``; exported API keys are replaced by fake ones (``fake_keys``).
- ``fake_http`` replaces the one HTTP seam (``ingest._get_json``) with deterministic FRED and Tiingo payloads.
- A socket guard makes any network connection fail unless the test is marked ``network``.
- The terminal summary prints the code line (G-16); unlike a report header, it survives ``-q``.
- ``realdata`` tests read this checkout's own build (``TC_ROOT_DIR`` at the repo root): they skip without one, and
  ``-m realdata`` without one is a usage error, so a run of skips can never pass the Mac gate.
"""

from __future__ import annotations

import shutil
import socket
import time
import zlib
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import pytest

from trading_crab_lib.platform import ingest

REPO = Path(__file__).resolve().parents[1]
BUILT = REPO / "data" / "checkpoints" / "monthly_raw.parquet"
FRED_KEY, TIINGO_KEY = "test-fred-key-123", "test-tiingo-key-456"


@pytest.fixture(autouse=True)
def tc_root(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh checkout root per test: config copied in, no data, no exported keys; ``realdata`` tests get the repo."""
    if request.node.get_closest_marker("realdata"):
        monkeypatch.setenv("TC_ROOT_DIR", str(REPO))
        return REPO
    (tmp_path / "config").mkdir()
    shutil.copy(REPO / "config" / "platform_settings.yaml", tmp_path / "config")
    monkeypatch.setenv("TC_ROOT_DIR", str(tmp_path))
    for name in ("FRED_API_KEY", "TIINGO_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


@pytest.fixture(autouse=True)
def fake_keys(tc_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake API keys, so a test can assert that a key never reaches a message, a log or the page."""
    monkeypatch.setenv("FRED_API_KEY", FRED_KEY)
    monkeypatch.setenv("TIINGO_API_KEY", TIINGO_KEY)


class FakeHttp:
    """Stands in for ``ingest._get_json``: deterministic payloads per series, every call recorded.

    FRED: observations dated the 1st, 1993-01 to the month before ``today``, one ``"."`` (1993-11). Tiingo: business
    days from 2004-01-02 to the requested ``endDate``. ``fail[name]`` makes one series fail: ``"error"`` (an HTTP
    error whose text carries the request, FRED's key included, as requests' own messages do), ``"empty"`` or
    ``"crash"`` (prices fall 95% in June 2010).
    """

    today = pd.Timestamp("2026-10-14")

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.fail: dict[str, str] = {}

    def __call__(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> object:
        params, headers = dict(params or {}), dict(headers or {})
        self.calls.append({"url": url, "params": params, "headers": headers})
        fred = url == ingest.FRED_URL
        name = params["series_id"] if fred else url.split("/")[-2]
        mode = self.fail.get(name)
        if mode == "error":
            raise ingest.SourceError(url, f"500 Server Error for url: {url}?{urlencode(params)}")
        if mode == "empty":
            return {"observations": []} if fred else []
        rng = np.random.default_rng([0, zlib.crc32(name.encode())])
        if fred:
            months = pd.date_range("1993-01-01", (self.today.to_period("M") - 1).to_timestamp(), freq="MS")
            values = [f"{v:.2f}" for v in 5 + np.cumsum(rng.normal(0, 0.1, len(months)))]
            values[10] = "."
            return {"observations": [{"date": f"{d:%Y-%m-%d}", "value": v} for d, v in zip(months, values)]}
        days = pd.bdate_range("2004-01-02", params["endDate"])
        prices = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(days))))
        if mode == "crash":
            prices[days >= "2010-06-15"] *= 0.05
        return [{"date": f"{d:%Y-%m-%d}T00:00:00.000Z", "close": p, "adjClose": p} for d, p in zip(days, prices)]


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> FakeHttp:
    """Route every fetch through ``FakeHttp``; no pauses."""
    fake = FakeHttp()
    monkeypatch.setattr(ingest, "_get_json", fake)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    return fake


@pytest.fixture(autouse=True)
def _no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly on any socket connection, unless the test is marked ``network``."""
    if request.node.get_closest_marker("network"):
        return

    def guard(*args: object, **kwargs: object) -> None:
        raise RuntimeError("network access in a test: mock the fetch, or mark the test @pytest.mark.network")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)


@pytest.hookimpl(trylast=True)  # after `-m` deselection, so `-m "not realdata"` never raises
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``realdata`` tests without a build here; refuse ``-m realdata`` without one."""
    marked = [item for item in items if item.get_closest_marker("realdata")]
    if not marked or BUILT.is_file():
        return
    markexpr = config.getoption("markexpr") or ""
    if "realdata" in markexpr and "not realdata" not in markexpr:
        raise pytest.UsageError(f"-m realdata needs a real build at {BUILT}: run tradingcrab build first")
    for item in marked:
        item.add_marker(pytest.mark.skip(reason="no build: run tradingcrab build first"))


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    """Name the code under test next to the result line (G-16)."""
    try:
        from trading_crab_lib.platform.code_version import code_version
    except ImportError as exc:
        terminalreporter.write_line(f"Code: unknown (trading_crab_lib does not import: {exc})")
        return
    terminalreporter.write_line(code_version())
