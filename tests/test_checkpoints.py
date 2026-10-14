"""M0: Parquet checkpoints behind the holdout fence (DECISIONS H-02, D-08)."""

from __future__ import annotations

import pandas as pd
import pytest

from trading_crab_lib.platform import checkpoints
from trading_crab_lib.platform.paths import data_dir

CUTOFF = "2020-12-31"


@pytest.fixture
def frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(["2020-11-30", "2020-12-31", "2021-01-31"])
    return pd.DataFrame({"gs10": [0.87, 0.93, 1.08], "SPY": [362.06, 373.88, 370.07]}, index=index)


def _same(left: pd.DataFrame, right: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(left, right, rtol=1e-9, atol=0, check_freq=False)


def test_the_fence_splits_at_the_cutoff(frame):
    checkpoints.save(frame, "monthly_raw", cutoff=CUTOFF)
    dev = pd.read_parquet(data_dir() / "checkpoints" / "monthly_raw.parquet")
    holdout = pd.read_parquet(data_dir() / "holdout" / "monthly_raw.parquet")
    assert dev.index.max() == pd.Timestamp("2020-12-31")  # the cutoff day itself is dev
    assert list(holdout.index) == [pd.Timestamp("2021-01-31")]


def test_load_is_dev_only_unless_the_holdout_is_asked_for(frame):
    checkpoints.save(frame, "monthly_raw", cutoff=CUTOFF)
    _same(checkpoints.load("monthly_raw"), frame.iloc[:2])
    _same(checkpoints.load("monthly_raw", include_holdout=True), frame)


def test_a_save_without_holdout_rows_removes_the_old_holdout_file(frame):
    checkpoints.save(frame, "monthly_raw", cutoff=CUTOFF)
    checkpoints.save(frame.iloc[:2], "monthly_raw", cutoff=CUTOFF)
    assert not (data_dir() / "holdout" / "monthly_raw.parquet").exists()
    _same(checkpoints.load("monthly_raw", include_holdout=True), frame.iloc[:2])


def test_every_save_overwrites_whole_never_merges(frame):
    checkpoints.save(frame, "monthly_raw", cutoff=CUTOFF)
    checkpoints.save(frame[["SPY"]], "monthly_raw", cutoff=CUTOFF)
    assert list(checkpoints.load("monthly_raw", include_holdout=True).columns) == ["SPY"]


@pytest.mark.parametrize("name", ["../x", "a/b", "", "x.parquet"])
def test_a_name_that_could_escape_the_data_folder_raises(frame, name):
    with pytest.raises(ValueError, match="checkpoint name"):
        checkpoints.save(frame, name, cutoff=CUTOFF)


def test_a_missing_checkpoint_names_tradingcrab_build():
    with pytest.raises(FileNotFoundError, match="tradingcrab build"):
        checkpoints.load("monthly_raw")
    with pytest.raises(FileNotFoundError, match="tradingcrab build"):
        checkpoints.load_meta("monthly_raw")


def test_meta_round_trips_with_a_build_time(frame):
    checkpoints.save(frame, "monthly_raw", cutoff=CUTOFF, meta={"publication_lags": {"gs10": 0, "SPY": 0}})
    meta = checkpoints.load_meta("monthly_raw")
    assert meta["meta"] == {"publication_lags": {"gs10": 0, "SPY": 0}}
    assert meta["built_at"]
