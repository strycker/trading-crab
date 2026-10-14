"""Repo hygiene: nothing generated, secret or legacy is tracked outside the frozen legacy/; the code keeps its shape.

Covers D-02, D-12, D-14 and MIG-01: no data, outputs, pickles or .env in git; images/ holds exactly the three crab
photos; legacy/ holds exactly its frozen manifest; clean_workspace.sh never removes a tracked or legacy file; every
library import targets trading_crab_lib.platform; every module is its docstring then the future import.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
IMAGES = {
    "images/glenn_weixuen_weitong_with_crab_300x400.png",
    "images/glenn_with_crab_2025_300x400.png",
    "images/glenn_with_crab_300x400.png",
}
_FINVIZ_DAYS = (
    "20240219 20240318 20240415 20240515 20240615 20240715 20240815 20240915 20241015 20241216 20250115 20250215 "
    "20250415 20250515 20250615 20250715 20250815 20250915 20251015 20251115 20251215 20260115 20260215"
).split()
_LEGACY_DATA = [f"finviz_snapshot_all_fields_{day}_001.csv" for day in _FINVIZ_DAYS] + [
    "fred_api_datasets_snapshot_20260216.csv", "fred_api_datasets_snapshot_20260216.pickle",
    "grok_quarter_classifications_20260201.csv", "grok_quarter_classifications_20260201.pickle",
    "grok_quarter_classifications_20260201.xlsx", "grok_quarter_classifications_20260216.csv",
    "grok_quarter_classifications_20260216.pickle", "multpl_datasets_snapshot_20260216.csv",
    "multpl_datasets_snapshot_20260216.pickle", "prepared_quarterly_data_smoothed_20260301.csv",
    "prepared_quarterly_data_smoothed_20260301.pickle", "standardized_quarterly_data_20260216.csv",
    "standardized_quarterly_data_20260216.pickle",
]
_LEGACY_NOTEBOOKS = [
    "step1_scrape_multpl_quarterly_data.ipynb", "step2_pull_fred_api_quarterly_data.ipynb",
    "step3_add_grok_suggested_labels.ipynb", "step4_combine_datasets_infer_missing_calc_derivs.ipynb",
    "step5_dimensional_reduction_and_clustering.ipynb",
]
LEGACY_MANIFEST = (
    {f"legacy/data/{name}" for name in _LEGACY_DATA}
    | {f"legacy/notebooks/{name}" for name in _LEGACY_NOTEBOOKS}
    | {"legacy/README.md"}
)

needs_git = pytest.mark.skipif(not (REPO / ".git").exists() or shutil.which("git") is None, reason="not a git checkout")


def _tracked(*pathspecs: str) -> list[str]:
    done = subprocess.run(["git", "ls-files", *pathspecs], cwd=REPO, check=True, capture_output=True, text=True)
    return done.stdout.splitlines()


def _src_py() -> list[Path]:
    """Every .py under src/, minus local build copies."""
    return sorted(p for p in (REPO / "src").rglob("*.py") if "build" not in p.relative_to(REPO).parts)


# ── tracked files ──


@needs_git
def test_nothing_generated_secret_or_pickled_is_tracked_outside_legacy():
    outside = [f for f in _tracked() if not f.startswith("legacy/")]
    assert not [f for f in outside if f.startswith(("data/", "outputs/"))]
    assert not [f for f in outside if f.endswith((".pkl", ".pickle", ".parquet", ".xlsx"))]
    assert not [f for f in _tracked() if Path(f).name == ".env"]


@needs_git
def test_images_are_the_three_crab_photos_and_nothing_else_is_binary():
    assert set(_tracked("images")) == IMAGES
    binary = {f for f in _tracked() if not f.startswith("legacy/") and b"\0" in (REPO / f).read_bytes()[:8192]}
    assert binary == IMAGES


@needs_git
def test_legacy_is_exactly_its_frozen_manifest():
    assert len(LEGACY_MANIFEST) == 42  # 41 moved files plus legacy/README.md
    assert set(_tracked("legacy")) == LEGACY_MANIFEST


@needs_git
def test_every_source_file_is_tracked():
    tracked = set(_tracked("src"))
    assert [p for p in _src_py() if str(p.relative_to(REPO)) not in tracked] == []


def _checkout(tmp_path: Path, files: tuple[str, ...]) -> None:
    """A minimal git checkout holding clean_workspace.sh and ``files`` (each containing "x"), all committed."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO / "scripts" / "clean_workspace.sh", tmp_path / "scripts")
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src" / "trading_crab_lib" / "platform").mkdir(parents=True)
    for rel in files:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
    for args in (["init", "-q"], ["add", "-A", "-f"], ["commit", "-q", "--no-verify", "-m", "fixture"]):
        subprocess.run([*git, *args], cwd=tmp_path, check=True, capture_output=True)


@needs_git
def test_clean_workspace_removes_generated_files_and_keeps_tracked_and_legacy(tmp_path):
    _checkout(tmp_path, ("legacy/data/x.csv", "src/keep.py", "src/gone.py"))
    for rel in ("data/checkpoints/y", "outputs/z", "src/pkg/__pycache__/m.pyc"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    (tmp_path / "src" / "gone.py").unlink()  # deleted by hand before the run: not the script's doing, so no failure
    done = subprocess.run(["bash", "scripts/clean_workspace.sh"], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "legacy" / "data" / "x.csv").read_text() == "x" and (tmp_path / "src" / "keep.py").exists()
    assert not (tmp_path / "data").exists() and not (tmp_path / "outputs").exists()
    assert not (tmp_path / "src" / "pkg" / "__pycache__").exists()


@needs_git
def test_clean_workspace_fails_on_a_tracked_file_it_removed_and_names_only_that_file(tmp_path):
    _checkout(tmp_path, ("data/tracked.csv", "src/gone.py"))  # a tracked file under data/, which the script removes
    (tmp_path / "src" / "gone.py").unlink()
    done = subprocess.run(["bash", "scripts/clean_workspace.sh"], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 1
    assert "git restore -- data/tracked.csv\n" in done.stderr and "gone.py" not in done.stderr
    assert "git restore ." not in done.stderr  # that would discard every unstaged edit


def test_clean_workspace_refuses_outside_a_checkout(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO / "scripts" / "clean_workspace.sh", tmp_path / "scripts")
    (tmp_path / "data").mkdir()
    done = subprocess.run(["bash", "scripts/clean_workspace.sh"], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 1 and (tmp_path / "data").exists()


# ── code shape ──


def test_every_module_is_its_docstring_then_the_future_import():
    for path in _src_py():
        body = ast.parse(path.read_text(encoding="utf-8")).body
        assert ast.get_docstring(ast.Module(body=body, type_ignores=[])), f"{path}: no module docstring"
        first = body[1] if len(body) > 1 else None
        assert isinstance(first, ast.ImportFrom) and first.module == "__future__", f"{path}: no future import after it"
        assert [a.name for a in first.names] == ["annotations"], path


def test_every_library_import_targets_the_platform():
    for path in [*_src_py(), *sorted((REPO / "tests").glob("*.py"))]:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            names += [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for name in names:
                if name.split(".")[0] == "trading_crab_lib":
                    assert name.startswith("trading_crab_lib.platform"), f"{path}: imports {name}"


def test_only_the_weekly_page_reads_past_the_holdout():
    callers = set()
    for path in _src_py():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.keyword) and node.arg == "include_holdout":
                if isinstance(node.value, ast.Constant) and node.value.value is True:
                    callers.add(path.relative_to(REPO).as_posix())
    assert callers == {"src/trading_crab_lib/platform/report.py"}


def test_no_source_names_the_scratch_repo():
    for path in (REPO / "src").rglob("*"):
        if path.is_file() and "build" not in path.relative_to(REPO).parts and path.suffix in (".py", ".md", ".toml"):
            assert not re.search(r"claude[-_]scratch", path.read_text(encoding="utf-8")), path


def test_every_library_package_is_listed_in_its_pyproject():
    text = (REPO / "src" / "trading_crab_lib" / "pyproject.toml").read_text(encoding="utf-8")
    listed = set(re.findall(r'"(trading_crab_lib(?:\.\w+)*)"', re.search(r"packages = \[(.*?)\]", text).group(1)))
    lib = REPO / "src" / "trading_crab_lib"
    found = {
        ".".join(("trading_crab_lib", *init.parent.relative_to(lib).parts))
        for init in lib.rglob("__init__.py")
        if "build" not in init.relative_to(lib).parts
    }
    assert found == listed


def test_the_four_rules_files_are_at_the_root():
    markers = {"CLAUDE.md": "P-07", "DECISIONS.md": "| G-20 |", "MODULE-MAP.md": "| M0 ", "LEARNINGS.md": "1. "}
    for name, marker in markers.items():
        assert marker in (REPO / name).read_text(encoding="utf-8"), name
