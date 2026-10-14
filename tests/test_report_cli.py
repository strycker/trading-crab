"""The tracer: ``tradingcrab build`` then ``tradingcrab weekly`` writes the page offline (D-04, G-16)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from trading_crab.cli import main
from trading_crab_lib.platform import ingest
from trading_crab_lib.platform.report import render

KEYS = ("test-fred-key-123", "test-tiingo-key-456")


@pytest.fixture
def fixed_build(fake_http, monkeypatch):
    """``tradingcrab build`` through ``fake_http`` on its fixed run date."""
    real = ingest.build
    monkeypatch.setattr(ingest, "build", lambda cfg: real(cfg, today=fake_http.today))
    return fake_http


def test_build_then_weekly_writes_the_page(tc_root, fixed_build, capsys):
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
        assert not any(key in text for key in KEYS)


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


def test_render_shows_run_date_data_through_and_latest_values():
    raw = pd.DataFrame({"gs10": [1.5, None], "SPY": [400.0, 410.0]}, index=pd.DatetimeIndex(["2024-01-31", "2024-02-29"]))
    page = render(raw, code_line="Code: test @ abc1234 — /x", run_date=date(2024, 3, 4))
    assert "Run date: 2024-03-04" in page
    assert "Data through month-end 2024-02-29 (latest complete month)" in page
    assert "## Latest values" in page
    assert "| gs10 | 1.5 | 2024-01-31 |" in page  # each value carries its own as-of date
