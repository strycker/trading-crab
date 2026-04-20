"""Shared fixtures for all tests."""

import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Checkpoint isolation
# ---------------------------------------------------------------------------
# All checkpoint I/O is redirected to a session-scoped tmp dir so pytest
# NEVER reads from or writes to the production data/checkpoints/ directory.
#
# _synthesize_features() is added at S2.3 once transforms.py exists.
# ---------------------------------------------------------------------------


def _synthesize_macro_raw(session_dir: Path) -> None:
    """Write a minimal synthetic macro_raw checkpoint to *session_dir*."""
    import trading_crab_lib.checkpoints as ckpt_mod

    rng = np.random.default_rng(0)
    n = 100
    idx = pd.date_range("2000-03-31", periods=n, freq="QE")
    sp500 = np.abs(rng.uniform(300, 5000, n)) + 200

    # fmt: off
    data: dict[str, np.ndarray] = {
        "sp500":        sp500,
        "sp500_adj":    sp500 * rng.uniform(0.95, 1.05, n),
        "dividend":     rng.uniform(10, 80, n),
        "div_yield":    rng.uniform(0.01, 0.06, n),
        "earnings":     rng.uniform(20, 200, n),
        "cape_shiller": rng.uniform(8, 40, n),
        "gdp":          rng.uniform(5000, 25000, n),
        "cpi":          rng.uniform(100, 320, n),
        "10yr_ustreas":  rng.uniform(1.0, 16.0, n),
        "us_cpi":       rng.uniform(100, 320, n),
        "book_value":   rng.uniform(100, 800, n),
        "price_sales":  rng.uniform(0.5, 5.0, n),
        "price_book":   rng.uniform(1.0, 6.0, n),
        "fred_gdp":     rng.uniform(5000, 25000, n),
        "fred_gnp":     rng.uniform(4800, 24000, n),
        "fred_baa":     rng.uniform(3.0, 12.0, n),
        "fred_aaa":     rng.uniform(2.5, 10.0, n),
        "fred_cpi":     rng.uniform(100, 320, n),
        "fred_gs10":    rng.uniform(1.0, 16.0, n),
        "fred_tb3ms":   rng.uniform(0.01, 10.0, n),
        "fred_vix":     rng.uniform(10, 80, n),
        "fred_unrate":  rng.uniform(3.0, 15.0, n),
        "fred_m2sl":    rng.uniform(3000, 25000, n),
        "fred_gs2":     rng.uniform(0.01, 10.0, n),
        "market_code":  np.zeros(n, dtype=float),
    }
    # fmt: on
    df = pd.DataFrame(data, index=idx)
    df.index.name = "date"
    cm = ckpt_mod.CheckpointManager(checkpoint_dir=session_dir)
    cm.save(df, "macro_raw")


def _synthesize_asset_prices(session_dir: Path) -> None:
    """Write a minimal synthetic asset_prices checkpoint to *session_dir*."""
    import trading_crab_lib.checkpoints as ckpt_mod

    try:
        from trading_crab_lib.config import load as _load_cfg

        cfg = _load_cfg()
        tickers = [str(t).upper() for t in cfg["assets"]["etfs"]][:8]
    except Exception:
        tickers = ["SPY", "GLD", "TLT", "QQQ", "IWM", "VNQ", "AGG", "USO"]

    rng = np.random.default_rng(42)
    index = pd.date_range("2000-03-31", periods=40, freq="QE")
    prices = pd.DataFrame(
        {ticker: rng.uniform(50, 400, len(index)) for ticker in tickers},
        index=index,
    )
    cm = ckpt_mod.CheckpointManager(checkpoint_dir=session_dir)
    cm.save(prices, "asset_prices")


@pytest.fixture(autouse=True, scope="session")
def _isolated_checkpoint_dir(tmp_path_factory: pytest.TempPathFactory):
    """Route all checkpoint I/O to a session-scoped tmp dir.

    Production data/checkpoints/ is never written to during pytest.
    """
    import trading_crab_lib.checkpoints as ckpt_mod

    session_dir = tmp_path_factory.mktemp("checkpoints", numbered=False)

    # Copy production checkpoints into session dir so read-based tests work
    prod_dir = ckpt_mod.CHECKPOINT_DIR
    if prod_dir.exists():
        for src in prod_dir.iterdir():
            shutil.copy2(src, session_dir / src.name)

    original_checkpoint_dir = ckpt_mod.CHECKPOINT_DIR
    ckpt_mod.CHECKPOINT_DIR = session_dir
    os.environ["TC_CHECKPOINT_DIR"] = str(session_dir)

    if not (session_dir / "macro_raw.parquet").exists():
        _synthesize_macro_raw(session_dir)
    if not (session_dir / "asset_prices.parquet").exists():
        _synthesize_asset_prices(session_dir)
    # _synthesize_features() added at S2.3 when transforms.py exists

    yield session_dir

    ckpt_mod.CHECKPOINT_DIR = original_checkpoint_dir
    os.environ.pop("TC_CHECKPOINT_DIR", None)


# ---------------------------------------------------------------------------
# Basic data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def quarterly_index():
    """20 quarter-end dates starting 2000-Q1."""
    return pd.date_range("2000-03-31", periods=20, freq="QE")


@pytest.fixture
def raw_macro_df(quarterly_index):
    """Minimal macro DataFrame with all columns needed by add_cross_ratios."""
    rng = np.random.default_rng(0)
    n = len(quarterly_index)
    # fmt: off
    return pd.DataFrame(
        {
            "sp500":     rng.uniform(800, 4000, n),
            "sp500_adj": rng.uniform(800, 4000, n),
            "dividend":  rng.uniform(10, 60, n),
            "div_yield": rng.uniform(0.01, 0.05, n),
            "gdp":       rng.uniform(8000, 22000, n),
            "cpi":       rng.uniform(150, 280, n),
            "fred_gdp":  rng.uniform(8000, 22000, n),
            "fred_gnp":  rng.uniform(7500, 21000, n),
            "fred_baa":  rng.uniform(3.0, 9.0, n),
            "fred_aaa":  rng.uniform(2.5, 8.0, n),
            "fred_cpi":  rng.uniform(150, 280, n),
        },
        index=quarterly_index,
    )
    # fmt: on


@pytest.fixture
def cluster_labels(quarterly_index):
    """Integer cluster labels cycling 0–4."""
    return pd.Series(
        np.tile(np.arange(5), len(quarterly_index) // 5 + 1)[: len(quarterly_index)],
        index=quarterly_index,
        name="balanced_cluster",
    )


@pytest.fixture
def asset_prices(quarterly_index):
    """Synthetic quarterly asset prices for 3 tickers."""
    rng = np.random.default_rng(1)
    n = len(quarterly_index)
    return pd.DataFrame(
        {
            "SPY": rng.uniform(80, 400, n),
            "GLD": rng.uniform(50, 200, n),
            "TLT": rng.uniform(70, 150, n),
        },
        index=quarterly_index,
    )
