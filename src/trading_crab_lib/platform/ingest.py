"""M1, the data build: ``build(cfg)`` saves ``monthly_raw`` (one column per FRED series and ticker) behind the fence.

Usage::

    from trading_crab_lib.platform import ingest
    from trading_crab_lib.platform.config import load
    raw = ingest.build(load())   # all rows; the dev rows land in data/checkpoints/, later ones in data/holdout/
"""

from __future__ import annotations

import pandas as pd

from trading_crab_lib.platform import checkpoints

_SKELETON_DATES = ("2020-11-30", "2020-12-31", "2021-01-31")


class BuildFailed(RuntimeError):
    """The build stopped before any write; the message names every failed source."""


def build(cfg: dict, *, today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Build, save and return ``monthly_raw``; ``today`` will bound the last complete month of the real fetch."""
    # ponytail: constant frame; 09.1-02 replaces it with the FRED + Tiingo fetch
    columns = [*cfg["fred"]["series"], *cfg["tickers"]]
    raw = pd.DataFrame(1.0, index=pd.DatetimeIndex(_SKELETON_DATES, name="date"), columns=columns)
    meta = {"publication_lags": cfg["publication_lags"]}
    checkpoints.save(raw, "monthly_raw", cutoff=cfg["holdout"]["cutoff"], meta=meta)
    return raw
