# CLAUDE.md: Trading-Crab project guide

Read this before writing code. Keep it at most 80 lines.

## What this is

Trading-Crab produces **weekly, guidance-only portfolio advice** that Glenn executes by hand in Fidelity: long-only, no
options, shorts or crypto. Two packages, one repo: `trading-crab-lib` (`src/trading_crab_lib/platform/`, all logic) and
`trading-crab` (`src/trading_crab/cli.py`, the `tradingcrab` command). `config/platform_settings.yaml` holds every
tuneable value. `legacy/` is a frozen reference from the retired quarterly pipeline.

## Governing principle: KISS (DECISIONS P-07)

The platform must be **human-readable, human-editable and human-testable by one person** with scripts and notebooks.
- Prefer the plainest honest design: fewer modules, fewer config switches, fewer bespoke checks, plain files.
- Spend rigor (mutation proofs, ruling records, verification layers) only on **decision-bearing numbers**.
- When rigor and readability conflict anywhere else, readability wins.
- **Size budget:** skeleton source at most 700 lines, at most 170 per file. Each later phase states its own budget.
- A new switch, module or check needs a reason a reader can state in one line.

## Where the rules live

| What | Where |
|---|---|
| Every decision, one row each: edit here first (G-20) | `DECISIONS.md` |
| Modules M0–M8: interface, skeleton, target, gate | `MODULE-MAP.md` |
| Mistakes not to repeat, each with its rule | `LEARNINGS.md` |
| Install and run | `README.md` |

## Working mode: lean MVP

- One module per phase, at most 3 plans; decisions are recorded as DECISIONS rows.
- Glenn creates and merges the PRs. Branches are `claude/<description>`; never push to `main`.
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
- `claude-scratch-work` is read-only reference and nothing imports it: rewrite from the architecture and LEARNINGS.md,
  never bulk-copy (G-19).

## How to run

```bash
pip install -e src/trading_crab_lib -e ".[dev]"     # one install, both packages (in a venv)
cp .env.example .env                                 # add FRED_API_KEY and TIINGO_API_KEY; never commit .env
tradingcrab build && tradingcrab weekly              # the page lands in outputs/reports/weekly_report.md
pytest tests -q -p no:cacheprovider && ruff check src tests
python -m build . --outdir dist-app && python -m build src/trading_crab_lib --outdir dist-lib
bash scripts/check_wheels.sh dist-lib dist-app       # both wheels install and import from site-packages
```
Every command and test run prints `Code: <branch> @ <commit> — <checkout>` first (G-16): check it before trusting a run.

## Honesty rules (do not break)

- **The 2021+ holdout is locked.** Development, tuning and model selection use data through 2020-12 only. Later rows
  live in `data/holdout/`; only the weekly page loads them (`include_holdout=True`, H-02).
- **Point-in-time data.** Every raw series has a `publication_lags` entry, applied once at ingestion. Features are
  causal only (trailing windows), proved by a truncation test. No look-ahead.
- **P&L uses month-end prices** (E-08). Monthly-average prices are model inputs only.
- **Fail loud** (DECISIONS D-08): a failed source stops the build before any write; every save overwrites whole.
- **Trial registry:** append-only once it exists (it arrives with the first budgeted run, no later than 9.4); every
  evaluated configuration is a row. A page never triggers an evaluation.

## Hard rules

- Never commit `.env` or API keys; secrets come only from environment variables. Show config with `redacted(cfg)`.
- Nothing generated is tracked: `data/`, `outputs/`, builds and notebook outputs stay out of git.
- No new pickle ever enters git (Parquet and JSON only). The six pickles in `legacy/data/` are frozen and never loaded.
- Never modify `legacy/` (frozen, CONTEXT D-14): no edits, no reads from code, no lint, no new files.
- No GitHub Release, tag or PyPI publish without Glenn.
- Never run Python, pytest or notebooks from `src/trading_crab_lib` (its `platform/` shadows the standard library).

## Code conventions

- Python 3.10+. Every module is its docstring, then `from __future__ import annotations`. `X | None`; type hints on
  public functions; `pathlib.Path` for paths; Parquet for frames.
- Library code uses `logging`, never `print`; only `cli.main()` prints. Catch specific exceptions; fail fast on config.
- Sections use `# ── Name ──` dividers; mark each intentional shortcut `# ponytail: <shortcut>; upgraded in 9.x`.
- Tests: flat `tests/`, offline (socket guard), under `TC_ROOT_DIR=tmp_path`, synthetic fixtures, floats at rel 1e-9,
  pandas 2 and 3 (`pct_change(fill_method=None)`); real-data tests carry the `realdata` marker.
- Lint: ruff (`E,F,W,I,UP`), line length 127. Notebooks call library code and define no logic.
- Model routing: keep architecture, review and correctness-critical code (look-ahead guards, CV splits, lag math) on
  the strongest model; delegate well-specified mechanical work and docs down.
