"""M2: the five backdrop features are causal (CONTEXT D-07: a truncation test, no performance number).

09.1-03 adds the allocation tests to this file.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trading_crab_lib.platform import features, ingest
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
