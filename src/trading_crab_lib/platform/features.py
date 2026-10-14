"""M2, the backdrop: five causal features from the lagged ``monthly_raw``. They set no weight (DECISIONS G-23).

Causal by construction: trailing windows only (no centring, no negative shift, no backfill), proved by the
truncation test (a feature at month t is the same whether or not later months exist). The input is the lagged
build, so ``unrate`` at t is already last month's release. Rows are consecutive month-ends, as the build makes them.

Usage::

    from trading_crab_lib.platform import features
    backdrop = features.compute(raw)   # a new frame with features.COLUMNS; raw is not changed
"""

from __future__ import annotations

import pandas as pd

COLUMNS = ["curve_10y3m", "credit_spread", "unrate_chg_12m", "spy_ret_12m", "spy_vol_6m"]


def compute(raw: pd.DataFrame) -> pd.DataFrame:
    """The five features on ``raw``'s index: yield curve, credit spread, unemployment change, SPY return and vol."""
    spy_monthly = raw["SPY"].pct_change(fill_method=None)
    return pd.DataFrame(
        {
            "curve_10y3m": raw["gs10"] - raw["tb3ms"],  # percentage points
            "credit_spread": raw["baa"] - raw["gs10"],  # percentage points
            "unrate_chg_12m": raw["unrate"] - raw["unrate"].shift(12),  # percentage points over 12 months
            "spy_ret_12m": raw["SPY"].pct_change(12, fill_method=None),  # SPY's own trailing return: market context
            "spy_vol_6m": spy_monthly.rolling(6).std() * 12**0.5,  # annualised, on month-end returns (E-11)
        },
        index=raw.index,
    )[COLUMNS]
