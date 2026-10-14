# Trading-Crab

![Glenn with crab](images/glenn_with_crab_2025_300x400.png)

Weekly, guidance-only portfolio advice from a monthly macro and price model. The platform recommends; a human trades
(long-only, by hand, in Fidelity). It is a personal tool, not investment advice for anyone else.

**Status: naive skeleton (Phase 9.1).** Every layer is present and deliberately simple: data build → features →
allocation → weekly page. Later phases upgrade one module at a time (`MODULE-MAP.md`).

## Install (from this checkout)

`trading-crab-lib` 0.2.0 is not on PyPI yet, so install both packages from the checkout in one command:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e src/trading_crab_lib -e ".[dev]"
pip install -e ".[notebook]"     # only for Jupyter
cp .env.example .env              # then add FRED_API_KEY and TIINGO_API_KEY
```

`.env` is ignored by git; never commit it.

## Run

```bash
tradingcrab build     # build the monthly data behind the 2021+ holdout fence
tradingcrab weekly    # write outputs/reports/weekly_report.md
tradingcrab --help
```

Every command prints `Code: <branch> @ <commit> — <checkout>` first, so you always see which code ran. `data/` and
`outputs/` are generated and never tracked.

## Test

```bash
pytest tests -q -p no:cacheprovider     # offline: synthetic data, no network, no keys
ruff check src tests
```

## Rules

- `CLAUDE.md`: KISS first, the honesty rules, hard rules and code conventions.
- `DECISIONS.md`: every decision, one row each (the live log).
- `MODULE-MAP.md`: modules M0–M8, their skeleton and target versions and their gates.
- `LEARNINGS.md`: mistakes not to repeat, each with the rule that prevents it.

## Layout

- `src/trading_crab_lib/platform/`: the library (`trading-crab-lib`); `src/trading_crab/cli.py`: the `tradingcrab`
  command (`trading-crab`); `config/platform_settings.yaml`: every tuneable value.
- `legacy/`: the retired quarterly pipeline's notebooks and data snapshots, frozen and never read by code; the full old
  tree is the tag `legacy/quarterly-final`.
- `bash scripts/clean_workspace.sh` removes everything generated (`data/`, `outputs/`, builds, caches) and never a
  tracked file.

## License

MIT (`LICENSE`).
