"""M0: paths, config and the code line (fail-fast config, keys from the environment, G-16)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from trading_crab_lib.platform import code_version as cv
from trading_crab_lib.platform import paths
from trading_crab_lib.platform.config import REQUIRED_SECTIONS, ConfigError, load, redacted

# ── config ──


def test_one_config_error_names_every_missing_section():
    cfg = load()
    partial = {k: v for k, v in cfg.items() if k not in ("holdout", "report")}
    with pytest.raises(ConfigError) as err:
        load(partial)
    assert "'holdout'" in str(err.value) and "'report'" in str(err.value)
    assert isinstance(err.value, ValueError)


def test_repo_config_has_every_section_and_a_string_cutoff():
    cfg = load()
    assert set(REQUIRED_SECTIONS) <= set(cfg)
    assert cfg["holdout"]["cutoff"] == "2020-12-31"  # quoted in YAML, so not a date


def test_an_exported_key_beats_dotenv_and_missing_keys_are_none(tc_root, monkeypatch):
    for name in ("FRED_API_KEY", "TIINGO_API_KEY"):
        monkeypatch.delenv(name)  # the autouse fake keys
    assert load()["keys"] == {"FRED_API_KEY": None, "TIINGO_API_KEY": None}
    (tc_root / ".env").write_text("FRED_API_KEY=from-dotenv\nTIINGO_API_KEY=tiingo-from-dotenv\n")
    monkeypatch.setenv("FRED_API_KEY", "exported-key")
    keys = load()["keys"]
    assert keys == {"FRED_API_KEY": "exported-key", "TIINGO_API_KEY": "tiingo-from-dotenv"}


def test_redacted_hides_both_keys_and_leaves_the_config_alone(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "fred-secret-123")
    monkeypatch.setenv("TIINGO_API_KEY", "tiingo-secret-456")
    cfg = load()
    shown = str(redacted(cfg))
    assert "fred-secret-123" not in shown and "tiingo-secret-456" not in shown
    assert cfg["keys"]["FRED_API_KEY"] == "fred-secret-123"


# ── paths ──


def test_tc_root_dir_wins_over_the_cwd_walk(tc_root, tmp_path_factory, monkeypatch):
    other = tmp_path_factory.mktemp("other")
    (other / "config").mkdir()
    shutil.copy(tc_root / "config" / "platform_settings.yaml", other / "config")
    monkeypatch.chdir(other)
    assert paths.root() == tc_root
    assert paths.data_dir() == tc_root / "data"
    assert paths.outputs_dir() == tc_root / "outputs"
    assert paths.config_path() == tc_root / "config" / "platform_settings.yaml"


def test_cwd_walk_finds_the_root_from_a_subfolder(tc_root, monkeypatch):
    monkeypatch.delenv("TC_ROOT_DIR")
    sub = tc_root / "notebooks" / "deeper"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert paths.root() == tc_root.resolve()


def test_no_config_anywhere_names_the_fix(tmp_path_factory, monkeypatch):
    monkeypatch.delenv("TC_ROOT_DIR")
    monkeypatch.chdir(tmp_path_factory.mktemp("empty"))
    with pytest.raises(FileNotFoundError, match="TC_ROOT_DIR"):
        paths.root()


def test_tc_root_dir_without_a_config_names_the_fix(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("TC_ROOT_DIR", str(tmp_path_factory.mktemp("bare")))
    with pytest.raises(FileNotFoundError, match="TC_ROOT_DIR"):
        load()


# ── code line (G-16) ──


@pytest.fixture
def git_repo(tmp_path_factory, monkeypatch) -> Path:
    """An isolated git repo on branch claude/try-me with a tracked copy of the module (no global git config)."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    repo = tmp_path_factory.mktemp("repo")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

    git("init", "-q", "-b", "claude/try-me")
    for key, value in (("user.name", "t"), ("user.email", "t@example.com"), ("commit.gpgsign", "false")):
        git("config", key, value)
    (repo / "src").mkdir()
    (repo / "src" / "code_version.py").write_text("one\n")
    git("add", "src/code_version.py")
    git("commit", "-q", "-m", "first")
    monkeypatch.setattr(cv, "_HERE", repo / "src")
    return repo


def test_code_line_names_branch_sha_and_checkout(git_repo):
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=git_repo, capture_output=True, text=True).stdout
    assert cv.code_version() == f"Code: claude/try-me @ {sha.strip()} — {git_repo.resolve()}"
    (git_repo / "src" / "code_version.py").write_text("two\n")
    assert "+ uncommitted changes" in cv.code_version()


def test_code_line_outside_a_git_checkout(tmp_path_factory, monkeypatch):
    bare = tmp_path_factory.mktemp("nogit")
    monkeypatch.setattr(cv, "_HERE", bare)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(bare.parent))
    assert cv.code_version() == f"Code: not a git checkout (or git unavailable) — {bare}"
