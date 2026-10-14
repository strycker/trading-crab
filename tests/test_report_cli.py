"""The tracer: ``tradingcrab build`` then ``tradingcrab weekly`` writes the page offline (D-04, G-16)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from trading_crab.cli import main
from trading_crab_lib.platform import features, ingest
from trading_crab_lib.platform.report import render


@pytest.fixture
def fixed_build(fake_http, monkeypatch):
    """``tradingcrab build`` through ``fake_http`` on its fixed run date."""
    real = ingest.build
    monkeypatch.setattr(ingest, "build", lambda cfg: real(cfg, today=fake_http.today))
    return fake_http


def test_build_then_weekly_writes_the_page(tc_root, fixed_build, fake_keys, capsys):
    assert main(["build"]) == 0
    built = capsys.readouterr()
    assert built.out.splitlines()[0].startswith("Code:")
    assert any("data through month-end 2026-09-30" in line for line in built.out.splitlines())
    assert main(["weekly"]) == 0
    weekly = capsys.readouterr()
    assert weekly.out.splitlines()[0].startswith("Code:")
    page = (tc_root / "outputs" / "reports" / "weekly_report.md").read_text()
    assert "Data through month-end 2026-09-30 (latest complete month)" in page
    assert page.splitlines()[2].startswith("Code:")
    for text in (built.out, built.err, weekly.out, weekly.err, page):
        assert not any(key in text for key in fake_keys.values())


def test_weekly_before_any_build_fails_and_names_the_fix(capsys):
    assert main(["weekly"]) == 1
    captured = capsys.readouterr()
    assert captured.out.splitlines()[0].startswith("Code:")
    assert "tradingcrab build" in captured.err


def test_help_prints_the_code_line_first(capsys):
    with pytest.raises(SystemExit) as done:
        main(["--help"])
    assert done.value.code == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("Code:")
    assert "build" in out and "weekly" in out


def test_render_shows_run_date_data_through_and_the_backdrop():
    index = pd.DatetimeIndex(["2024-01-31", "2024-02-29"])
    raw = pd.DataFrame({"gs10": [1.5, None], "SPY": [400.0, 410.0]}, index=index)
    backdrop = pd.DataFrame({column: [0.5, None] for column in features.COLUMNS}, index=index)
    page = render(raw, backdrop, code_line="Code: test @ abc1234 — /x", run_date=date(2024, 3, 4))
    assert "Run date: 2024-03-04" in page
    assert "Data through month-end 2024-02-29 (latest complete month)" in page
    assert "| curve_10y3m | 0.5000 | 2024-01-31 |" in page  # each value carries its own as-of date
    assert "| spy_ret_12m (market context) | 0.5000 | 2024-01-31 |" in page


def test_the_page_shows_the_causal_backdrop_and_no_performance_term(tc_root, fixed_build):
    assert main(["build"]) == 0 and main(["weekly"]) == 0
    page = (tc_root / "outputs" / "reports" / "weekly_report.md").read_text()
    assert "## Backdrop (causal features; they set no weight)" in page
    assert all(f"| {column}" in page for column in features.COLUMNS)
    assert "spy_ret_12m (market context)" in page
    for term in ("backtest", "strategy return", "sharpe", "drawdown", "cagr"):  # CONTEXT D-07
        assert term not in page.lower(), term


def test_weekly_refuses_data_built_with_another_lag_table(tc_root, fixed_build, capsys):
    assert main(["build"]) == 0
    settings = tc_root / "config" / "platform_settings.yaml"
    text = settings.read_text()
    assert "  unrate: 1 " in text
    settings.write_text(text.replace("  unrate: 1 ", "  unrate: 2 "))
    capsys.readouterr()
    assert main(["weekly"]) == 1
    assert "tradingcrab build" in capsys.readouterr().err
    assert not (tc_root / "outputs" / "reports" / "weekly_report.md").exists()
