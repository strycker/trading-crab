"""Parquet checkpoints behind the holdout fence.

``save(df, name, cutoff=...)`` writes rows on or before the cutoff to ``data/checkpoints/NAME.parquet``, later
rows to ``data/holdout/NAME.parquet`` and a sidecar ``data/checkpoints/NAME.meta.json`` (``built_at``, ``meta``).
Every save overwrites the whole checkpoint, never merges (DECISIONS D-08: a merge refilled columns from a stale
copy). ``load(name)`` returns dev rows only; ``include_holdout=True`` is the explicit opt-in to look past the
cutoff, and only the weekly page uses it (DECISIONS H-02: the fence is on fitting, not looking).

Usage::

    from trading_crab_lib.platform import checkpoints
    checkpoints.save(frame, "monthly_raw", cutoff=cfg["holdout"]["cutoff"], meta={"publication_lags": lags})
    dev = checkpoints.load("monthly_raw")
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from trading_crab_lib.platform.paths import data_dir

log = logging.getLogger(__name__)

_NAME = re.compile(r"[A-Za-z0-9_]+")
_MISSING = "no checkpoint {name!r} at {path}: run `tradingcrab build` first"


def _paths(name: str) -> tuple[Path, Path, Path]:
    """(dev parquet, holdout parquet, meta json) for a validated name."""
    if not _NAME.fullmatch(name):
        raise ValueError(f"checkpoint name {name!r} must match [A-Za-z0-9_]+")
    dev_dir, holdout_dir = data_dir() / "checkpoints", data_dir() / "holdout"
    return dev_dir / f"{name}.parquet", holdout_dir / f"{name}.parquet", dev_dir / f"{name}.meta.json"


def save(df: pd.DataFrame, name: str, *, cutoff: str, meta: dict[str, Any] | None = None) -> Path:
    """Split ``df`` (DatetimeIndex) at ``cutoff``, overwrite both sides and the sidecar; return the dev path."""
    dev_path, holdout_path, meta_path = _paths(name)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(f"checkpoint {name!r} needs a DatetimeIndex, got {type(df.index).__name__}")
    cutoff_ts = pd.Timestamp(cutoff)
    dev, holdout = df.loc[df.index <= cutoff_ts], df.loc[df.index > cutoff_ts]
    dev_path.parent.mkdir(parents=True, exist_ok=True)
    dev.to_parquet(dev_path)
    if len(holdout):
        holdout_path.parent.mkdir(parents=True, exist_ok=True)
        holdout.to_parquet(holdout_path)
    else:
        holdout_path.unlink(missing_ok=True)  # a stale holdout must never outlive the save that replaced it
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta_path.write_text(json.dumps({"built_at": built_at, "meta": meta or {}}, indent=2) + "\n", encoding="utf-8")
    log.info("saved %s: %d dev rows, %d holdout rows (cutoff %s)", name, len(dev), len(holdout), cutoff_ts.date())
    return dev_path


def load(name: str, *, include_holdout: bool = False) -> pd.DataFrame:
    """Dev rows of a checkpoint; with ``include_holdout=True`` the holdout rows too, in date order."""
    dev_path, holdout_path, _ = _paths(name)
    if not dev_path.is_file():
        raise FileNotFoundError(_MISSING.format(name=name, path=dev_path))
    frame = pd.read_parquet(dev_path)
    if include_holdout and holdout_path.is_file():
        frame = pd.concat([frame, pd.read_parquet(holdout_path)]).sort_index()
    return frame


def load_meta(name: str) -> dict[str, Any]:
    """The sidecar of a checkpoint: ``{"built_at": ..., "meta": {...}}``."""
    _, _, meta_path = _paths(name)
    if not meta_path.is_file():
        raise FileNotFoundError(_MISSING.format(name=name, path=meta_path))
    return json.loads(meta_path.read_text(encoding="utf-8"))
