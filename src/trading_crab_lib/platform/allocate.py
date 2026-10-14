"""M3, the target mix: inverse-vol weights over the risky assets, scaled to a vol target, the rest in cash.

Volatility is measured on month-end returns (DECISIONS E-11): the last ``window`` of them. Each asset's weight is
proportional to 1 / its vol; the risky sleeve is then scaled down (never up) until its annualised vol is at most
``vol_target``, and cash takes the remainder (DECISIONS G-23). Long-only by construction.

Usage::

    from trading_crab_lib.platform.allocate import target_weights
    weights = target_weights(raw[cfg["tickers"]], window=36, vol_target=0.10)   # index: the tickers, then "cash"
"""

from __future__ import annotations

import pandas as pd


def target_weights(prices: pd.DataFrame, *, window: int, vol_target: float) -> pd.Series:
    """Weights for ``prices``' columns (in order) plus ``"cash"``; all >= 0, summing to 1.

    Raises ``ValueError`` with fewer than ``window`` complete month-end returns, or an asset with no volatility.
    """
    returns = prices.pct_change(fill_method=None).dropna()
    if len(returns) < window:
        raise ValueError(f"need {window} month-end returns, have {len(returns)}")
    returns = returns.iloc[-window:]
    vols = returns.std()
    if not (vols > 0).all():
        raise ValueError(f"no volatility in the last {window} returns of: {', '.join(vols.index[~(vols > 0)])}")
    # ponytail: inverse-vol, no costs, band or hysteresis; upgraded in 9.4/9.5
    mix = (1 / vols) / (1 / vols).sum()
    sleeve_vol = float((returns @ mix).std()) * 12**0.5  # annualised
    risky = mix * min(1.0, vol_target / sleeve_vol)
    cash = max(0.0, 1.0 - float(risky.sum()))  # clamped: float dust gave -2.2e-16 in 13 of 200 seeds
    return pd.concat([risky, pd.Series({"cash": cash})])
