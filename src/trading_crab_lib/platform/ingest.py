"""M1, the data build: FRED and Tiingo month-ends, publication lags applied once, saved behind the holdout fence.

``build(cfg)`` fetches the config's FRED monthly series and Tiingo daily adjusted closes, keeps complete month-ends
only (a label on or after the run date is an unfinished month), shifts each column by its ``publication_lags`` entry
(here, once, nowhere else) and saves ``monthly_raw`` behind the fence, the lag table in the meta sidecar.

Fail loud (DECISIONS D-08): a missing key stops the build before any request; every failed series is collected
into one ``BuildFailed`` and nothing is written; there is no fallback source. Keys reach no message: the Tiingo
token travels only in the ``Authorization`` header, and FRED's key (a query parameter) is redacted.

Usage::

    from trading_crab_lib.platform import ingest
    from trading_crab_lib.platform.config import load
    raw = ingest.build(load())   # every row; checkpoints.load("monthly_raw") gives the dev rows only
"""

from __future__ import annotations

import logging
import time
from datetime import date

import pandas as pd
import requests

from trading_crab_lib.platform import checkpoints
from trading_crab_lib.platform.config import KEY_NAMES, ConfigError

log = logging.getLogger(__name__)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
TIINGO_URL = "https://api.tiingo.com/tiingo/daily"
_TRIES = 3  # attempts per request while the API answers 429 (rate limited)
_PAUSE_SECONDS = 1.0  # between Tiingo tickers; the 429 backoff doubles from here
_RETURN_LIMITS = (-0.90, 1.00)  # a month-end return outside these is a broken series, not a market move (D-08)


class SourceError(RuntimeError):
    """One series could not be fetched or parsed; ``.source`` names it."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"{source}: {reason}")
        self.source = source


class BuildFailed(RuntimeError):
    """The build stopped before any write; the message names every failed series."""


def _redact(text: str, *secrets: str | None) -> str:
    """``text`` with every non-empty secret replaced by ``***``."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


# ── fetch ──


def _get_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> object:
    """GET ``url`` and return its JSON: the one HTTP seam (tests replace it). A 429 is retried, 3 tries at most."""
    for attempt in range(_TRIES):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:  # its text may carry the full URL, FRED key included
            raise SourceError(url, f"request failed: {exc}") from exc
        if response.status_code != 429:
            break
        log.warning("%s rate limited the request (try %d of %d)", url, attempt + 1, _TRIES)
        if attempt < _TRIES - 1:
            time.sleep(_PAUSE_SECONDS * 2**attempt)
    if response.status_code != 200:
        raise SourceError(url, f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise SourceError(url, "the response is not JSON") from exc


def _usable(series: pd.Series, name: str) -> pd.Series:
    if series.dropna().empty:
        raise SourceError(name, "the response has no usable rows")
    return series


def fred_series(series_id: str, *, api_key: str, start: str, today: pd.Timestamp) -> pd.Series:
    """One FRED monthly series on month-end labels before ``today``; ``"."`` (no observation) becomes NaN."""
    # ponytail: FRED's latest vintage (revisions included), not ALFRED's as-published values; upgraded in 9.2
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json", "observation_start": start}
    payload = _get_json(FRED_URL, params=params)
    try:
        observations = payload["observations"]
        values = [pd.to_numeric(o["value"], errors="coerce") for o in observations]
        index = pd.to_datetime([o["date"] for o in observations]).to_period("M").to_timestamp("M")
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceError(series_id, f"malformed FRED response ({exc!r})") from exc
    series = pd.Series(values, index=index, dtype=float, name=series_id).sort_index()
    return _usable(series[series.index < today], series_id)


def tiingo_prices(ticker: str, *, api_key: str, start: str, today: pd.Timestamp) -> pd.Series:
    """One ticker's adjusted close at each complete month-end before ``today``; a wild month-end return raises."""
    params = {"startDate": start, "endDate": f"{today:%Y-%m-%d}"}
    rows = _get_json(f"{TIINGO_URL}/{ticker}/prices", params=params, headers={"Authorization": f"Token {api_key}"})
    try:
        index = pd.to_datetime([row["date"] for row in rows], utc=True).tz_localize(None).normalize()
        daily = pd.Series([row["adjClose"] for row in rows], index=index, dtype=float)  # no close fallback
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceError(ticker, f"malformed Tiingo rows, adjClose required ({exc!r})") from exc
    daily = daily[~daily.index.duplicated(keep="last")].sort_index().dropna()
    month_end = daily.resample("ME").last()
    month_end = _usable(month_end[month_end.index < today], ticker).rename(ticker)
    returns = month_end.pct_change(fill_method=None)
    wild = returns[(returns <= _RETURN_LIMITS[0]) | (returns >= _RETURN_LIMITS[1])]
    if len(wild):
        raise SourceError(ticker, f"month-end return {wild.iloc[0]:+.1%} on {wild.index[0]:%Y-%m-%d} is not plausible")
    return month_end


# ── lags and build ──


def _check_lags(columns: list[str] | pd.Index, lags: dict[str, int]) -> None:
    bad = [c for c in columns if not isinstance(lags.get(c), int) or lags[c] < 0]
    if bad:
        raise ConfigError(f"publication_lags needs a whole number of months >= 0 for {bad} (config/platform_settings.yaml)")


def apply_lags(frame: pd.DataFrame, lags: dict[str, int]) -> pd.DataFrame:
    """Shift each column by its lag in months, by timestamp: a value moves to the month-end it became public."""
    _check_lags(frame.columns, lags)
    shifted = {c: frame[c].shift(lags[c], freq="ME") if lags[c] else frame[c] for c in frame.columns}
    return pd.concat(shifted, axis=1).sort_index()


def build(cfg: dict, *, today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Fetch every series, apply the lags once, save ``monthly_raw`` behind the fence; return all its rows.

    ``today`` is the run date (default ``data.end_date``, else today): month-end labels on or after it are
    unfinished months and are dropped, both before and after the lags.
    """
    lags, keys = cfg["publication_lags"], cfg["keys"]
    _check_lags([*cfg["fred"]["series"], *cfg["tickers"]], lags)
    missing = [name for name in KEY_NAMES if not keys.get(name)]
    if missing:
        raise BuildFailed(f"build stopped before any request: set {' and '.join(missing)} (environment or .env)")
    today = pd.Timestamp(today if today is not None else cfg["data"].get("end_date") or date.today()).normalize()
    start, fred_key, tiingo_key = cfg["data"]["start_date"], keys["FRED_API_KEY"], keys["TIINGO_API_KEY"]
    series, failures = {}, []
    for column, series_id in cfg["fred"]["series"].items():
        try:
            series[column] = fred_series(series_id, api_key=fred_key, start=start, today=today)
        except SourceError as exc:
            failures.append(f"{column} (FRED {series_id}): {exc}")
    for n, ticker in enumerate(cfg["tickers"]):
        if n:
            time.sleep(_PAUSE_SECONDS)
        try:
            series[ticker] = tiingo_prices(ticker, api_key=tiingo_key, start=start, today=today)
        except SourceError as exc:
            failures.append(f"{ticker} (Tiingo): {exc}")
    if failures:
        raise BuildFailed(_redact("build stopped before any write:\n  " + "\n  ".join(failures), fred_key, tiingo_key))
    raw = apply_lags(pd.concat(series, axis=1), lags)
    raw = raw.loc[raw.index < today].rename_axis("date")
    checkpoints.save(raw, "monthly_raw", cutoff=cfg["holdout"]["cutoff"], meta={"publication_lags": lags})
    return raw
