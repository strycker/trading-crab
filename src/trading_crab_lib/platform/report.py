"""M4, the weekly page: ``run(cfg)`` renders the built data into ``outputs/reports/weekly_report.md``.

The page: code line, run date, data-through date, a STALE banner past ``report.max_age_days``, the target mix (M3),
the regime and scoreboard placeholders, then the causal backdrop (M2). No performance number (CONTEXT D-07).

This is the one module that reads past the holdout cutoff (``include_holdout=True``): the page is live scoring,
and the fence is on fitting, not looking (DECISIONS H-02). It refuses data built with a different
``publication_lags`` table than the config's, since that data is not what the config describes.

Usage::

    from trading_crab_lib.platform import report
    path = report.run(cfg)   # after `tradingcrab build`
    raw, backdrop, weights = report.inputs(cfg)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from trading_crab_lib.platform import checkpoints, features
from trading_crab_lib.platform.allocate import target_weights
from trading_crab_lib.platform.code_version import code_version
from trading_crab_lib.platform.config import ConfigError
from trading_crab_lib.platform.paths import outputs_dir

_LABELS = {"spy_ret_12m": "spy_ret_12m (market context)"}  # SPY's own return, not a result of any strategy


def inputs(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """``(raw, backdrop, weights)`` from the build: every row, the five features and the target mix."""
    if checkpoints.load_meta("monthly_raw")["meta"].get("publication_lags") != cfg["publication_lags"]:
        raise ConfigError("monthly_raw was built with a different publication_lags table: run tradingcrab build")
    raw = checkpoints.load("monthly_raw", include_holdout=True)
    allocation = cfg["allocation"]
    weights = target_weights(raw[cfg["tickers"]], window=allocation["vol_window"], vol_target=allocation["vol_target"])
    return raw, features.compute(raw), weights


def render(raw: pd.DataFrame, backdrop: pd.DataFrame, weights: pd.Series, *, cfg: dict, code_line: str, run_date: date) -> str:
    """The page as Markdown; the same inputs and run date always give the same text."""
    through, max_age = raw.index.max(), cfg["report"]["max_age_days"]
    age = (pd.Timestamp(run_date) - through).days
    allocation = cfg["allocation"]
    lines = [
        "# Trading-Crab weekly page",
        "",
        code_line,
        "",
        f"Run date: {run_date:%Y-%m-%d}",
        f"Data through month-end {through:%Y-%m-%d} (latest complete month)",
        "",
    ]
    if age > max_age:
        lines += [f"**STALE:** the data is {age} days old (limit {max_age}): run `tradingcrab build`.", ""]
    lines += [
        "Naive skeleton: a wiring check, not evidence.",
        "",
        "## Target mix (guidance only; trades are placed by hand)",
        "",
        "| Asset | Target % |",
        "|---|---|",
        *(f"| {name} | {100 * weight:.1f}% |" for name, weight in weights.items()),
        f"| Total | {100 * weights.sum():.1f}% |",
        "",
        f"Method: inverse volatility on the last {allocation['vol_window']} month-end returns, scaled so the mix's"
        f" annual volatility is at most {allocation['vol_target']:.0%}; the rest is cash (DECISIONS G-23).",
        "",
        "Regime view: none in the skeleton (arrives with 9.6-9.8)",
        "",
        "Scoreboard: not yet measured (arrives with 9.4)",
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
    """Inputs, render, write: the weekly page from the build."""
    raw, backdrop, weights = inputs(cfg)
    return write(render(raw, backdrop, weights, cfg=cfg, code_line=code_version(), run_date=run_date or date.today()))
