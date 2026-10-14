"""The end-to-end notebook: stripped, logic-free, signed off in its last cell, and it runs top to bottom (SC1, SC6).

No Jupyter kernel is needed: every code cell is ``exec``-ed in one namespace on a synthetic build, as Run All would.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from trading_crab_lib.platform import ingest
from trading_crab_lib.platform.config import load

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "E2E_skeleton.ipynb"
STRIP = "jupyter nbconvert --clear-output --inplace notebooks/E2E_skeleton.ipynb"
PERFORMANCE_TERMS = ("backtest", "strategy return", "sharpe", "drawdown", "cagr")  # CONTEXT D-07


def _cells() -> list[dict]:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def _source(cell: dict) -> str:
    return "".join(cell["source"])


def _code() -> list[str]:
    return [_source(cell) for cell in _cells() if cell["cell_type"] == "code"]


def test_the_notebook_is_stripped_and_ends_in_a_sign_off_cell():
    cells = _cells()
    assert len(cells) == 8
    assert cells[0]["cell_type"] == "markdown" and "tradingcrab build" in _source(cells[0])
    for cell in cells:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None, f"strip outputs first: {STRIP}"
    last = cells[-1]
    assert last["cell_type"] == "markdown"
    assert all(word in _source(last) for word in ("Sign-off", "Date", "Verdict", "Reasoning"))


def test_the_notebook_calls_the_library_and_defines_no_logic():
    code = "\n".join(_code())
    assert "report.inputs(cfg)" in code
    for banned in (".save(", "print(cfg)", "def ", "class ", "lambda", "display(", "matplotlib", "plt.", "sys.path"):
        assert banned not in code, banned
    assert not re.search(r"^\s*[%!]", code, re.MULTILINE)  # no magics or shell lines: the cells must exec as Python
    assert not re.search(r"^\s*cfg\s*$", code, re.MULTILINE)  # a bare cfg would echo the API keys


def test_the_notebook_names_no_performance_term():
    text = "\n".join(_source(cell) for cell in _cells()).lower()
    assert not [term for term in PERFORMANCE_TERMS if term in text]


def test_the_notebook_runs_top_to_bottom_on_a_synthetic_build(fake_http, fake_keys, capsys):
    ingest.build(load(), today=fake_http.today)
    capsys.readouterr()
    namespace: dict = {"__name__": "__notebook__"}
    for index, source in enumerate(_code()):  # a failure's traceback names the cell
        exec(compile(source, f"E2E_skeleton.ipynb code cell {index}", "exec"), namespace)
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("Code:")
    *rows, (name, total) = re.findall(r"^\| (\w+) \| ([0-9.]+)% \|$", out, re.MULTILINE)
    assert name == "Total" and total == f"{sum(float(pct) for _, pct in rows):.1f}"  # the sum of the printed rows
    assert "Scoreboard: not yet measured" in out
    assert not any(key in out for key in fake_keys.values())
    assert not [term for term in PERFORMANCE_TERMS if term in out.lower()]
