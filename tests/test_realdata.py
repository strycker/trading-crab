"""The Mac gate: checks on the real build in this checkout's ``data/`` (``tradingcrab build``, then ``pytest -m realdata``).

Without a build these tests skip, and ``pytest -m realdata`` stops with a usage error (see conftest).
"""

from __future__ import annotations

import pandas as pd
import pytest

from trading_crab_lib.platform import checkpoints, report
from trading_crab_lib.platform.config import load
from trading_crab_lib.platform.paths import data_dir

pytestmark = pytest.mark.realdata


def test_the_real_build_has_every_column_and_respects_the_fence():
    cfg = load()
    cutoff = pd.Timestamp(cfg["holdout"]["cutoff"])
    dev = checkpoints.load("monthly_raw")
    holdout = pd.read_parquet(data_dir() / "holdout" / "monthly_raw.parquet")
    assert list(dev.columns) == [*cfg["fred"]["series"], *cfg["tickers"]]
    assert dev.notna().any().all()  # every series delivered values (D-08)
    assert dev.index.max() <= cutoff < holdout.index.min()


def test_the_weekly_page_renders_from_the_real_build():
    page = report.run(load()).read_text(encoding="utf-8")
    assert page.splitlines()[2].startswith("Code:")
    assert "## Backdrop (causal features; they set no weight)" in page
    assert "| Total | 100.0% |" in page
