"""M2: the five backdrop features are causal (CONTEXT D-07: a truncation test, no performance number).
M3: the inverse-vol target mix is long-only, sums to 1 and meets its vol target (DECISIONS G-23, E-11).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trading_crab_lib.platform import features, ingest
from trading_crab_lib.platform.allocate import target_weights
from trading_crab_lib.platform.config import load


@pytest.fixture
def raw(fake_http) -> pd.DataFrame:
    """Every row of a fake build (dev and holdout), as the weekly page sees it."""
    return ingest.build(load(), today=fake_http.today)


def test_features_are_causal_by_truncation(raw):
    before = raw.copy()
    full = features.compute(raw)
    assert list(full.columns) == features.COLUMNS
    months = raw.index[::7]  # from the first month, so a backfill into the warm-up rows is caught too
    assert full.loc[months[months >= "2006-01-01"]].notna().all().all()  # from 2006 every feature has a value
    for t in months:  # a feature at t may use nothing after t
        pd.testing.assert_series_equal(features.compute(raw.loc[:t]).loc[t], full.loc[t], rtol=1e-9, atol=0)
    pd.testing.assert_frame_equal(raw, before)  # the input is untouched


def test_the_formulas_on_a_hand_checked_frame():
    index = pd.date_range("2020-01-31", periods=13, freq="ME")
    spy = 100 * 1.01 ** np.arange(13)
    raw = pd.DataFrame({"gs10": 2.0, "tb3ms": 0.5, "baa": 4.0, "unrate": np.arange(13) / 10, "SPY": spy}, index=index)
    last = features.compute(raw).iloc[-1]
    assert last["curve_10y3m"] == pytest.approx(1.5, rel=1e-9)
    assert last["credit_spread"] == pytest.approx(2.0, rel=1e-9)
    assert last["unrate_chg_12m"] == pytest.approx(1.2, rel=1e-9)
    assert last["spy_ret_12m"] == pytest.approx(1.01**12 - 1, rel=1e-9)
    assert last["spy_vol_6m"] == pytest.approx(0.0, abs=1e-12)  # a constant 1% month has no volatility


# ── M3: target weights ──

TICKERS = ["SPY", "TLT", "IAU", "USO"]  # config order, not alphabetical


def _prices(seed: int, months: int = 60, vols: tuple[float, ...] = (0.04, 0.03, 0.05, 0.09)) -> pd.DataFrame:
    """Random-walk month-end prices, one column per ticker, with the given monthly vols."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.005, 1.0, (months, len(vols))) * np.array(vols)
    index = pd.date_range("2015-01-31", periods=months, freq="ME")
    return pd.DataFrame(100 * np.exp(np.cumsum(returns, axis=0)), index=index, columns=TICKERS[: len(vols)])


@pytest.mark.parametrize("seed", range(5))
def test_weights_are_long_only_and_sum_to_one(seed):
    weights = target_weights(_prices(seed), window=36, vol_target=0.10)
    assert (weights >= 0).all()
    assert weights["cash"] >= 0
    assert weights.sum() == pytest.approx(1.0, rel=1e-9)


def test_twice_the_vol_gets_half_the_weight():
    index = pd.date_range("2015-01-31", periods=40, freq="ME")
    calm = np.random.default_rng(7).normal(0.0, 0.01, 40)
    prices = pd.DataFrame({"SPY": 100 * np.cumprod(1 + calm), "TLT": 100 * np.cumprod(1 + 2 * calm)}, index=index)
    weights = target_weights(prices, window=36, vol_target=1.0)  # a target this high never scales
    assert weights["SPY"] > weights["TLT"]
    assert weights["SPY"] / weights["TLT"] == pytest.approx(2.0, rel=1e-9)


def test_volatile_inputs_are_scaled_to_the_target_and_leave_cash():
    prices = _prices(3, vols=(0.10, 0.08, 0.12, 0.15))
    weights = target_weights(prices, window=36, vol_target=0.10)
    risky = weights.drop("cash")
    returns = prices.pct_change(fill_method=None).dropna().iloc[-36:]
    assert (returns @ risky).std() * 12**0.5 == pytest.approx(0.10, rel=1e-6)
    assert weights["cash"] > 0


def test_fewer_return_rows_than_the_window_raise():
    with pytest.raises(ValueError, match="need 36 month-end returns, have 35"):
        target_weights(_prices(0, months=36), window=36, vol_target=0.10)


def test_the_index_is_the_columns_in_order_then_cash():
    weights = target_weights(_prices(1), window=36, vol_target=0.10)
    assert list(weights.index) == [*TICKERS, "cash"]
