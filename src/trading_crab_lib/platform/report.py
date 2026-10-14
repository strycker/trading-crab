"""M4, the weekly page: ``run(cfg)`` renders the built data into ``outputs/reports/weekly_report.md``.

This is the one module that reads past the holdout cutoff (``include_holdout=True``): the page is live scoring,
and the fence is on fitting, not looking (DECISIONS H-02). It refuses data built with a different
``publication_lags`` table than the config's, since that data is not what the config describes.

Usage::

    from trading_crab_lib.platform import report
    path = report.run(cfg)   # after `tradingcrab build`
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from trading_crab_lib.platform import checkpoints, features
from trading_crab_lib.platform.code_version import code_version
from trading_crab_lib.platform.config import ConfigError
from trading_crab_lib.platform.paths import outputs_dir

_LABELS = {"spy_ret_12m": "spy_ret_12m (market context)"}  # SPY's own return, not a result of any strategy


def render(raw: pd.DataFrame, backdrop: pd.DataFrame, *, code_line: str, run_date: date) -> str:
    """The page as Markdown: title, code line, run date, data-through date and the feature backdrop."""
    lines = [
        "# Trading-Crab weekly page",
        "",
        code_line,
        "",
        f"Run date: {run_date:%Y-%m-%d}",
        f"Data through month-end {raw.index.max():%Y-%m-%d} (latest complete month)",
        "",
        "Naive skeleton: nothing on this page is advice yet.",
        "",
        "## Backdrop (causal features; they set no weight)",
        "",
        "| Feature | Value | As of |",
        "|---|---|---|",
    ]
    for column in backdrop.columns:
        values, label = backdrop[column].dropna(), _LABELS.get(column, column)
        if values.empty:
            lines.append(f"| {label} | n/a | n/a |")
        else:
            lines.append(f"| {label} | {values.iloc[-1]:.4f} | {values.index[-1]:%Y-%m-%d} |")
    return "\n".join(lines) + "\n"


def write(text: str) -> Path:
    """Overwrite ``outputs/reports/weekly_report.md`` with ``text``; return its path."""
    path = outputs_dir() / "reports" / "weekly_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(cfg: dict, *, run_date: date | None = None) -> Path:
    """Check the build's lag table, load ``monthly_raw`` (dev and holdout rows), render and write the page."""
    if checkpoints.load_meta("monthly_raw")["meta"].get("publication_lags") != cfg["publication_lags"]:
        raise ConfigError("monthly_raw was built with a different publication_lags table: run tradingcrab build")
    raw = checkpoints.load("monthly_raw", include_holdout=True)
    page = render(raw, features.compute(raw), code_line=code_version(), run_date=run_date or date.today())
    return write(page)
