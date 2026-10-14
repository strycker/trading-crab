"""M4, the weekly page: ``run(cfg)`` renders the built data into ``outputs/reports/weekly_report.md``.

This is the one module that reads past the holdout cutoff (``include_holdout=True``): the page is live scoring,
and the fence is on fitting, not looking (DECISIONS H-02).

Usage::

    from trading_crab_lib.platform import report
    path = report.run(cfg)   # after `tradingcrab build`
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from trading_crab_lib.platform import checkpoints
from trading_crab_lib.platform.code_version import code_version
from trading_crab_lib.platform.paths import outputs_dir


def render(raw: pd.DataFrame, *, code_line: str, run_date: date) -> str:
    """The page as Markdown: title, code line, run date, data-through date, latest value of each column."""
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
        "## Latest values",
        "",
        "| Series | Value | As of |",
        "|---|---|---|",
    ]
    for column in raw.columns:
        values = raw[column].dropna()
        if values.empty:
            lines.append(f"| {column} | n/a | n/a |")
        else:
            lines.append(f"| {column} | {values.iloc[-1]:.6g} | {values.index[-1]:%Y-%m-%d} |")
    return "\n".join(lines) + "\n"


def write(text: str) -> Path:
    """Overwrite ``outputs/reports/weekly_report.md`` with ``text``; return its path."""
    path = outputs_dir() / "reports" / "weekly_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(cfg: dict, *, run_date: date | None = None) -> Path:
    """Load ``monthly_raw`` (dev and holdout rows), render and write the page."""
    raw = checkpoints.load("monthly_raw", include_holdout=True)
    return write(render(raw, code_line=code_version(), run_date=run_date or date.today()))
