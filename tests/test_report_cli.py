"""The tracer: ``tradingcrab build`` then ``tradingcrab weekly`` writes the page offline (D-04, G-16)."""

from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd
import pytest

from trading_crab.cli import main
from trading_crab_lib.platform import features, ingest, report
from trading_crab_lib.platform.allocate import target_weights
from trading_crab_lib.platform.config import load
from trading_crab_lib.platform.report import render


@pytest.fixture
def fixed_build(fake_http, monkeypatch):
    """``tradingcrab build`` through ``fake_http`` and ``tradingcrab weekly``, both on its fixed run date (no clock)."""
    real_build, real_run = ingest.build, report.run
    monkeypatch.setattr(ingest, "build", lambda cfg: real_build(cfg, today=fake_http.today))
    monkeypatch.setattr(report, "run", lambda cfg: real_run(cfg, run_date=fake_http.today.date()))
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
    assert "Data through month-end 2026-09-30 (the latest month-end with every series)" in page
    assert "Missing at month-end" not in page  # every series reached September
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


def _render_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    index = pd.DatetimeIndex(["2024-01-31", "2024-02-29"])
    raw = pd.DataFrame({"gs10": [1.5, None], "SPY": [400.0, 410.0]}, index=index)
    backdrop = pd.DataFrame({column: [0.5, None] for column in features.COLUMNS}, index=index)
    weights = pd.Series({"SPY": 0.25, "TLT": 0.35, "IAU": 0.2, "USO": 0.1, "cash": 0.1})
    return raw, backdrop, weights


def _page(run_date: date) -> str:
    return render(*_render_inputs(), cfg=load(), code_line="Code: test @ abc1234 — /x", run_date=run_date)


def test_render_shows_run_date_data_through_and_the_backdrop():
    page = _page(date(2024, 3, 4))
    assert "Run date: 2024-03-04" in page
    assert "Data through month-end 2024-01-31 (the latest month-end with every series)" in page  # gs10 is late
    assert "Missing at month-end 2024-02-29: gs10" in page
    assert "| curve_10y3m | 0.5000 | 2024-01-31 |" in page  # each value carries its own as-of date
    assert "| spy_ret_12m (market context) | 0.5000 | 2024-01-31 |" in page


def test_render_lists_the_mix_in_config_order_then_cash_with_the_total():
    lines = _page(date(2024, 3, 4)).splitlines()
    rows = [line for line in lines if re.fullmatch(r"\| \w+ \| [0-9.]+% \|", line)]
    assert rows == [
        "| SPY | 25.0% |",
        "| TLT | 35.0% |",
        "| IAU | 20.0% |",
        "| USO | 10.0% |",
        "| cash | 10.0% |",
        "| Total | 100.0% |",
    ]
    assert "## Target mix (guidance only; trades are placed by hand)" in lines
    assert "Regime view: none in the skeleton (arrives with 9.6-9.8)" in lines
    assert "Scoreboard: not yet measured (arrives with 9.4)" in lines


def test_stale_banner_past_max_age_only():
    assert load()["report"]["max_age_days"] == 45
    assert "**STALE:**" in _page(date(2024, 2, 29) + timedelta(days=60))
    assert "STALE" not in _page(date(2024, 2, 29) + timedelta(days=10))
    assert "**STALE:** the data is 49 days old" in _page(date(2024, 3, 20))  # aged from 01-31, the date every series has


def test_two_renders_with_the_same_inputs_are_identical():
    assert _page(date(2024, 3, 4)) == _page(date(2024, 3, 4))


def test_weekly_puts_the_inverse_vol_mix_on_the_page(tc_root, fixed_build):
    assert main(["build"]) == 0 and main(["weekly"]) == 0
    raw, backdrop, weights = report.inputs(load())
    assert list(weights.index) == ["SPY", "TLT", "IAU", "USO", "cash"]
    assert weights.sum() == pytest.approx(1.0, rel=1e-9)
    assert list(backdrop.columns) == features.COLUMNS and raw.index.max() == pd.Timestamp("2026-09-30")
    page = (tc_root / "outputs" / "reports" / "weekly_report.md").read_text()
    assert "| Total | 100.0% |" in page
    assert all(f"| {name} | {100 * weights[name]:.1f}% |" in page for name in weights.index)
    assert "Scoreboard: not yet measured (arrives with 9.4)" in page
    assert "STALE" not in page  # the fake build's run date is 14 days after its data


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



def _mix(cfg: dict, prices: pd.DataFrame) -> pd.Series:
    """``target_weights`` with the config's allocation settings."""
    return target_weights(prices, window=cfg["allocation"]["vol_window"], vol_target=cfg["allocation"]["vol_target"])


def test_a_late_fred_series_moves_the_data_date_back_and_is_named(tc_root, fixed_build):
    fixed_build.fail["GS10"] = "late"  # FRED has not published September's 10-year yield yet
    assert main(["build"]) == 0 and main(["weekly"]) == 0
    page = (tc_root / "outputs" / "reports" / "weekly_report.md").read_text()
    assert "Data through month-end 2026-08-31 (the latest month-end with every series)" in page
    assert "Missing at month-end 2026-09-30: gs10" in page
    cfg = load()
    raw, _, weights = report.inputs(cfg)
    tickers = cfg["tickers"]
    pd.testing.assert_series_equal(weights, _mix(cfg, raw.loc[:"2026-08-31", tickers]), rtol=1e-9, atol=0)
    assert not weights.equals(_mix(cfg, raw[tickers]))  # every ticker has September, yet the mix is as of the page's date


def test_a_late_ticker_gives_weights_as_of_the_pages_date(tc_root, fixed_build):
    fixed_build.fail["USO"] = "late"  # Tiingo has no September month-end for USO
    assert main(["build"]) == 0 and main(["weekly"]) == 0
    page = (tc_root / "outputs" / "reports" / "weekly_report.md").read_text()
    assert "Data through month-end 2026-08-31 (the latest month-end with every series)" in page
    assert "Missing at month-end 2026-09-30: USO" in page
    cfg = load()
    raw, _, weights = report.inputs(cfg)
    tickers = cfg["tickers"]
    pd.testing.assert_series_equal(weights, _mix(cfg, raw.loc[:"2026-08-31", tickers]), rtol=1e-9, atol=0)
    with pytest.raises(ValueError, match="USO"):  # allocate refuses a missing last month rather than dropping it
        _mix(cfg, raw[tickers])
