"""M1: the FRED + Tiingo build: complete month-ends, lags applied once, the fence, fail loud, keys in no message.

Every test is offline: ``fake_http`` replaces the one HTTP seam, or ``requests.get`` is faked for the retry tests.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from trading_crab_lib.platform import checkpoints, ingest
from trading_crab_lib.platform.config import load
from trading_crab_lib.platform.paths import data_dir

FRED_KEY, TIINGO_KEY = "test-fred-key-123", "test-tiingo-key-456"
COLUMNS = ["gs10", "tb3ms", "baa", "unrate", "SPY", "TLT", "IAU", "USO"]


def _nothing_written() -> bool:
    return not data_dir().exists() or not any(data_dir().rglob("*"))


# ── parsing and complete month-ends ──


def test_fred_dot_is_missing_and_the_first_of_the_month_lands_on_its_month_end(fake_http):
    series = ingest.fred_series("GS10", api_key=FRED_KEY, start="1993-01-01", today=fake_http.today)
    assert series.index[0] == pd.Timestamp("1993-01-31")
    assert series.index[-1] == pd.Timestamp("2026-09-30")  # the 2026-09-01 observation
    assert np.isnan(series.loc["1993-11-30"]) and series.notna().sum() == len(series) - 1


@pytest.mark.parametrize(("today", "last"), [("2026-10-31", "2026-09-30"), ("2026-11-01", "2026-10-31")])
def test_tiingo_keeps_only_complete_month_ends(fake_http, today, last):
    prices = ingest.tiingo_prices("SPY", api_key=TIINGO_KEY, start="1993-01-01", today=pd.Timestamp(today))
    assert prices.index[-1] == pd.Timestamp(last)  # a label on or after the run date is an unfinished month
    rows = fake_http(f"{ingest.TIINGO_URL}/SPY/prices", params={"endDate": today})
    september = [r["adjClose"] for r in rows if r["date"].startswith("2026-09")]
    assert prices.loc["2026-09-30"] == pytest.approx(september[-1], rel=1e-9)  # the month's last close


# ── publication lags ──


def test_apply_lags_moves_unrate_one_month_and_leaves_lag_zero_alone():
    index = pd.date_range("2020-01-31", periods=4, freq="ME")
    frame = pd.DataFrame({"gs10": [1.0, 2.0, 3.0, 4.0], "unrate": [3.5, 3.6, 4.4, 14.7]}, index=index)
    out = ingest.apply_lags(frame, {"gs10": 0, "unrate": 1})
    for t in index[1:]:
        assert out.loc[t, "unrate"] == pytest.approx(frame.loc[t - pd.offsets.MonthEnd(1), "unrate"], rel=1e-9)
    pd.testing.assert_series_equal(out["gs10"].dropna(), frame["gs10"], rtol=1e-9, atol=0, check_freq=False)


@pytest.mark.parametrize("lags", [{"gs10": 0}, {"gs10": 0, "baa": -1}])
def test_apply_lags_refuses_a_column_without_a_lag_or_with_a_negative_one(lags):
    frame = pd.DataFrame({"gs10": [1.0], "baa": [2.0]}, index=pd.DatetimeIndex(["2020-01-31"]))
    with pytest.raises(ValueError, match="baa"):
        ingest.apply_lags(frame, lags)


def test_the_unrate_lag_is_at_least_one_month():
    assert load()["publication_lags"]["unrate"] >= 1  # literal floor: BLS publishes month m during m+1


def test_the_build_saves_lagged_fenced_monthly_raw_in_config_order(fake_http):
    cfg = load()
    raw = ingest.build(cfg, today=fake_http.today)
    assert list(raw.columns) == COLUMNS
    assert raw.index.max() == pd.Timestamp("2026-09-30")
    assert checkpoints.load("monthly_raw").index.max() == pd.Timestamp("2020-12-31")
    assert pd.read_parquet(data_dir() / "holdout" / "monthly_raw.parquet").index.min() == pd.Timestamp("2021-01-31")
    assert checkpoints.load_meta("monthly_raw")["meta"] == {"publication_lags": cfg["publication_lags"]}
    unlagged = ingest.fred_series("UNRATE", api_key=FRED_KEY, start="1993-01-01", today=fake_http.today)
    same = {"rtol": 1e-9, "atol": 0, "check_names": False, "check_freq": False}
    a_month_earlier = unlagged.reindex(raw.index - pd.offsets.MonthEnd(1)).set_axis(raw.index)
    pd.testing.assert_series_equal(raw["unrate"], a_month_earlier, **same)  # unrate at t is the value of t - 1 month
    gs10 = ingest.fred_series("GS10", api_key=FRED_KEY, start="1993-01-01", today=fake_http.today)
    pd.testing.assert_series_equal(raw["gs10"], gs10.reindex(raw.index), **same)  # lag 0: unchanged


# ── fail loud ──


def test_a_missing_key_stops_the_build_before_any_request(fake_http, monkeypatch):
    monkeypatch.delenv("TIINGO_API_KEY")
    with pytest.raises(ingest.BuildFailed, match="TIINGO_API_KEY"):
        ingest.build(load(), today=fake_http.today)
    assert fake_http.calls == []
    assert _nothing_written()


def test_every_failed_series_is_named_in_one_error_and_nothing_is_written(fake_http):
    fake_http.fail.update(BAA="error", USO="error")
    with pytest.raises(ingest.BuildFailed) as err:
        ingest.build(load(), today=fake_http.today)
    message = str(err.value)
    assert message.startswith("build stopped before any write")
    assert "BAA" in message and "USO" in message
    assert len(fake_http.calls) == 8  # every series was tried before the build gave up
    assert _nothing_written()


@pytest.mark.parametrize("name", ["UNRATE", "IAU"])
def test_an_empty_source_fails_the_build(fake_http, name):
    fake_http.fail[name] = "empty"
    with pytest.raises(ingest.BuildFailed, match=name):
        ingest.build(load(), today=fake_http.today)
    assert _nothing_written()


def test_an_implausible_month_end_return_fails_the_build(fake_http):
    fake_http.fail["IAU"] = "crash"  # the D-08 incident: a -98% gold month shipped with no error
    with pytest.raises(ingest.BuildFailed, match="IAU"):
        ingest.build(load(), today=fake_http.today)
    assert _nothing_written()


# ── secrets ──


def test_keys_never_reach_an_error_and_the_tiingo_token_rides_the_header_only(fake_http):
    fake_http.fail["GS10"] = "error"  # its text carries the request URL, FRED key included
    with pytest.raises(ingest.BuildFailed) as err:
        ingest.build(load(), today=fake_http.today)
    assert FRED_KEY not in str(err.value) and "***" in str(err.value)
    tiingo = [call for call in fake_http.calls if call["url"].startswith(ingest.TIINGO_URL)]
    assert len(tiingo) == 4
    for call in tiingo:
        assert TIINGO_KEY not in call["url"] + str(call["params"])
        assert call["headers"] == {"Authorization": f"Token {TIINGO_KEY}"}
    assert ingest._redact(f"a {FRED_KEY} b {TIINGO_KEY}", FRED_KEY, TIINGO_KEY, None) == "a *** b ***"


# ── the HTTP seam: rate limits ──


class _Response:
    def __init__(self, status: int, payload: object = None) -> None:
        self.status_code, self._payload = status, payload

    def json(self) -> object:
        return self._payload


def _fake_get(monkeypatch, replies: list[_Response]) -> list[dict]:
    calls: list[dict] = []

    def get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return replies[min(len(calls), len(replies)) - 1]

    monkeypatch.setattr(ingest.requests, "get", get)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    return calls


def test_a_rate_limit_is_retried_and_then_succeeds(monkeypatch):
    rows = [{"date": "2024-01-31T00:00:00.000Z", "adjClose": 1.0}]
    calls = _fake_get(monkeypatch, [_Response(429), _Response(429), _Response(200, rows)])
    prices = ingest.tiingo_prices("SPY", api_key=TIINGO_KEY, start="2024-01-01", today=pd.Timestamp("2024-02-15"))
    assert len(calls) == 3 and list(prices.index) == [pd.Timestamp("2024-01-31")]
    assert all(call["timeout"] == 30 and "verify" not in call for call in calls)  # default TLS, bounded wait


def test_three_rate_limits_name_the_ticker(monkeypatch):
    calls = _fake_get(monkeypatch, [_Response(429)])
    with pytest.raises(ingest.SourceError, match="SPY"):
        ingest.tiingo_prices("SPY", api_key=TIINGO_KEY, start="2024-01-01", today=pd.Timestamp("2024-02-15"))
    assert len(calls) == 3
