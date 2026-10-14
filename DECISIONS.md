# Decisions

**The live decision log** (G-20, CONTEXT D-09): once the Phase 9.1 PR merges, edit this file first. One row per
decision, same IDs as before. To change a decision, edit its row and add `CHANGED yyyy-mm-dd (who)`; git keeps the old
text. The long-form history and the retired numbers stay in `claude-scratch-work` (`platform_design/DECISIONS.md`).

**Status:** `live` (in force now), `skeleton` (its naive version is part of the 9.1 skeleton), `target 9.x` (arrives
with that phase's module), `record` (a past result or event, kept for its lesson).

## Product and scope

| ID | Decision | Why | Status |
|---|---|---|---|
| P-01 | Guidance only: the platform recommends and Glenn trades by hand in Fidelity. Long-only; no options, shorts, crypto or MLPs. | Personal investor, not a trading desk | live |
| P-02 | Benchmark: buy-and-hold SPY **net of avoided drawdowns**. | The reason to exist is sidestepping 2000/2008-class damage | live |
| P-03 | Monthly modelling spine, weekly scoring, nothing under one month. | The edge thesis lives at monthly+ horizons | live |
| P-04 | Free data only in v1: FRED and Tiingo's free tier (keyed REST APIs); paid providers are not dependencies. CHANGED 2026-10-14 (9.1-01, per the approved 9.1 plan): Tiingo's free tier is the price source. | Cost; keyed REST APIs work on the corporate VPN where scrapers are blocked | live |
| P-05 | The platform was designed in `claude-scratch-work` and is rebuilt here from scratch (G-17); the legacy quarterly pipeline stays behind. | Heavy-dev tooling there, clean production repo here | record |
| P-06 | Tracer-bullet build: every layer present and naive first, then upgrade one module at a time. | A usable skeleton early | live |
| P-07 | **KISS.** Readable, editable and testable by one person with Python scripts and notebooks. The simplest honest design wins: fewer modules, switches and bespoke checks, plain files. Rigor only on decision-bearing numbers; elsewhere readability wins. | We drifted toward machinery a single user cannot read or maintain | live |

## L0: Data

| ID | Decision | Why | Status |
|---|---|---|---|
| D-01 | "Model the index, trade the ETF": one research series per asset class, mapped to a tradable ticker. | Long histories (1962+) that ETFs lack | target 9.2 |
| D-02 | Core 5 classes: equities (SPY), long duration (TLT), gold (IAU), oil (USO), cash. | Minimal cross-asset spine | live |
| D-03 | Ratio-splice at overlap windows; log the resolved source of every series. | Continuity without level jumps | target 9.2 |
| D-04 | ALFRED vintages only for revision-heavy agency series; every other series gets a publication-lag shift. Shifts first, vintages later. | Revisions leak future information | target 9.2 |
| D-05 | **Every series is lagged to its publication date**: a `publication_lags` entry per column, applied once at ingestion; an unlisted column fails the build. | Look-ahead (CR-03): three series entered features unlagged for seven phases | live |
| D-06 | A small frozen taxonomy of named, interpretable features. | Few features a human can read | target 9.3 |
| D-07 | Pre-vintage GDP (before 1991-12-04) uses fallback lag 3 months. | Lag 1 made GDP visible about two months early | target 9.2 |
| D-08 | **A failed source fails the build before any write**, naming every failure; every save overwrites whole (no merge); a fallback is a failure unless explicitly allowed (`--allow-missing`, 9.2). | A lost gold source plus merge-on-save shipped a −98.07% gold return with no error | live |
| D-09 | Gold's research series is the World Bank monthly average (1960+); P&L on month-end prices. | One free source reachable everywhere, longest history | target 9.2 |

## Honesty rails

| ID | Decision | Why | Status |
|---|---|---|---|
| H-01 | Physical 2021+ holdout: rows after the cutoff live in `data/holdout/`, which the default loader never reads. | Unlimited peeking destroys the out-of-sample test | skeleton |
| H-02 | The fence is on **fitting**, not **looking**: the weekly page (live scoring) may read the full span; it is the only `include_holdout=True` caller. | Must see live decay | live |
| H-03 | Append-only trial registry; one row per evaluated configuration. | Multiple-testing denominator | target 9.4 |
| H-04 | Walk-forward only; purged and embargoed CV; a 12-month label embargo for L2. | No temporal leakage | live |
| H-05 | Deflated Sharpe uses the whole registry since the true-zero epoch (H-12). | Honest selection penalty | target 9.4 |
| H-06 | Per-phase trial budgets, declared before the runs, amendable only in advance; unspent budget expires. | Makes search-creep visible | target 9.4 |
| H-07 | Non-selecting fits (serving refits, observational legs) write `NO_REGISTRY` and spend no budget. | They select nothing | target 9.4 |
| H-08 | Ablation arms count toward N but not toward the Sharpe variance. | Otherwise the DSR hurdle collapses | target 9.4 |
| H-09 | The deflated-Sharpe hurdle is the one quality gate; reported, not blocking, before the MVP. | One honest answer to "is it any good?" | target 9.4 |
| H-10 | Floats compared at rel 1e-9, abs 0; never bit-exact. | macOS and Linux BLAS differ by a few ULP | live |
| H-11 | A check that can only confirm is a defect; core invariants ship with a mutation that turns them red. | 13 confirm-only checks found in Phase 8 | live |
| H-12 | Registry true-zero epoch: the 48 earlier trials are archived in `claude-scratch-work` (tag `model/pre-reset-2026-10`); they ran on the same 1972–2020 data, so early hurdles understate the burden. | Restart the search count, disclosed | record |

## L1 / L2: Regimes

| ID | Decision | Why | Status |
|---|---|---|---|
| L1-01 | Statistical jump model is the labeler (t-HMM only a benchmark); two-sided labels are offline ground truth. | Stable labels, one persistence knob | target 9.6 |
| L1-02 | K = 6, λ = 10 on the frozen common-support features; the walk-forward driver and evaluation use the same features. | K = 5 missed the occupancy band | target 9.6 |
| L1-03 | One sub-floor state is allowed under a recurrence exemption (crises are rare but real). | Crisis states | target 9.6 |
| L1-05 | Occupancy band 8–35% per state, report-only. | Semantic states, not forced balance | target 9.6 |
| L1-06 | State ids are aligned across refits as part of the labeler's API (CR-02). | Refits renumbered the states | target 9.6 |
| L2-01 | Calibrated multinomial logistic nowcaster, purged CV, causal features. | Simple, calibrated baseline | target 9.7 |
| L2-02 | Feature admission must not shrink training to a constant model; count distinct outputs. | A constant posterior passed for 231 months | target 9.7 |
| L2-03 | Bayes filter over the nowcaster posterior, divided by its own training class prior. | Memory without a new model | target 9.7 |
| L2-04 | Leakage is governed by causal invariance: a value at t must not change when rows after t are removed (the truncation test). | The one test that catches look-ahead | live |

## L3 / L4: Assets, allocation, page

| ID | Decision | Why | Status |
|---|---|---|---|
| A-01 | Returns-by-regime tables plus an EWMA vol layer are the L3 baseline. | The naive baseline to beat | target 9.4 |
| A-02 | Vol targeting at **10% annual vol**; the rest is cash. | Defensive by design | skeleton |
| A-03 | Hysteresis 0.70 / 0.40 on the active regime label. | Stops label flicker reaching the page | target M9+ |
| A-04 | A 5-percentage-point no-trade band, the same function in backtest and serving. | Filtered churn became trades | target 9.5 |
| A-05 | 10 bps cost per rebalance on traded notional; turnover reported. | Light-touch realism | target 9.4 |
| A-06 | The weekly page is always Markdown; email is opt-in; holdings are per-account weight YAML. | Human in the loop | skeleton |
| A-08 | The page prints the count of distinct posterior vectors. | A constant model never passes as live | target 9.7 |
| A-09 | Neutral posture: no active regime, one sentence, no rows. | Unlabelled rows misled | target 9.8 |
| A-10 | A minimal daily tripwire (3 signals), advisory. | Crash avoidance is the point | target 9.5 |
| A-11 | The page always prints the target allocation (class, ticker, target %). | Without accounts the page never said what to hold | skeleton |
| A-12 | Staleness is judged per series against its own publication lag; a STALE banner, never a refusal or imputation. | A ragged current month looked stale | skeleton |
| A-13 | MVP-1 core allocation is the no-regime path. | The regime tilt lost to the ablation (E-06, E-12) | live |
| A-14 | The weekly regime view stays suspended until a served nowcaster is input-responsive. | A constant posterior is no information | live |
| A-15 | A mode switch trades to the new target in full and says so on the page. | Banding against the old book made a hybrid | target 9.8 |

## Evaluation

| ID | Decision | Why | Status |
|---|---|---|---|
| E-01 | Baseline gauntlet: SPY, 60/40, Faber 10-month SMA, plus the no-regime ablation. | Does the regime layer pay rent? | target 9.4 |
| E-02 | The joint-lift criterion was routed L1-only; L2 legs were observational. | The L2 posterior was too weak | record |
| E-03 | Joint lift: met as a measurement, failed as a result. | Neither leg cleared the DSR hurdle | record |
| E-05 | Superseded numbers are amended old → new with a date, never overwritten; git history does the rest. | Audit trail | live |
| E-06 | 8.1 result: on point-in-time data the regime tilt did **not** beat the no-regime ablation. | The pre-declared rule, applied once | record |
| E-07 | Returns from monthly-average prices carry an intra-month move; averages are model inputs only. | Residual look-ahead in P&L | live |
| E-08 | **P&L on month-end prices.** | Fixes E-07 | live |
| E-09 | Core-mix rule: leave the no-regime mix only if a baseline beats it on both terminal log wealth and max drawdown (1972–2020, net 10 bps). | Rule fixed before the numbers | target 9.4 |
| E-10 | Faber's signal and returns use month-end prices. | A fair candidate | target 9.4 |
| E-11 | Estimate vol on month-end returns, not averages (averages ran 13–17% low). | Measured in 8.3 | skeleton |
| E-12 | 8.3 result on month-end P&L: the tilt still lost to the ablation; the core mix stands. | Both pre-declared rules, one budgeted run | record |

## Process

| ID | Decision | Why | Status |
|---|---|---|---|
| G-01 | Each module ships its notebook with a plain Markdown human sign-off cell. | Human understanding and gating | live |
| G-02 | Plotting lives in `platform/plotting/`; notebooks call it and hold no plotting logic. | Reuse and testability | target 9.2 |
| G-06 | The regime view stays advisory until a rebuilt model beats the no-regime ablation on point-in-time data, walk-forward ≤2020-12. | E-06: the tilt lost | live |
| G-11 | Live weekly and serving state is machine-local and untracked. | It holds the operator's real book | live |
| G-14 | **Clean-slate reset (08.5).** Tag `model/pre-reset-2026-10` on `4e49652` freezes the old tree. Nothing generated lives in git: `/data/` and `/outputs/` are ignored and notebook outputs are stripped. Read the old tree with `git restore --source=model/pre-reset-2026-10 --worktree -- data outputs` (in `claude-scratch-work`). Real-data tests carry the `realdata` marker and skip without a build; the record pins retired. | Start over from a clean slate; models are not tracked unless tagged | record |
| G-15 | **Phase 9 order (D-07).** Phases 9.1–9.8, one module each (M0..M7). M8 (honesty) has no phase of its own and moves with its first importer: the holdout fence with the skeleton's data build (9.1); walk-forward with the full data spine (9.2); the registry, budgets and DSR with M3 (9.4), and the state tool with its first real need. CHANGED 2026-10-12 (Glenn, 08.5): the registry moves at its real first importer. CHANGED 2026-10-13 (Glenn, 9.1 research): the skeleton defers the state tool, so nothing in 9.1 reads the registry. M9+ (A-03, REG-01) stays backlog until MVP-2. | KISS: code moves when something uses it | live |
| G-16 | **Every run names its code.** Each CLI prints `Code: <branch> @ <short sha>[ + uncommitted changes] — <checkout>` as its first line, and pytest prints the same line next to its result. Git runs from the package's own folder, so an editable install of another clone shows. | Glenn ran a gate on `main` while meaning the 8.5 branch (2026-10-12) | live |
| G-17 | **One production repo.** `strycker/trading-crab` holds all production code and both packages (`trading-crab` app, `trading-crab-lib` library). The separate `strycker/trading-crab-lib` repo gets a pointer README and is archived. `claude-scratch-work` is for planning and reference only. Legacy quarterly code, tracked data and pickles are removed, not migrated (amended by CONTEXT D-14: the old notebooks and data snapshots are frozen in `legacy/`). The package path stays `trading_crab_lib.platform.*`. `tradingcrab` is the single front door. | One source of truth; both PyPI pages already point here | live |
| G-18 | **The rules travel with the code.** This repo carries a short CLAUDE.md (KISS P-07, honesty and hard rules), DECISIONS.md, MODULE-MAP.md and LEARNINGS.md. The GSD `.planning/` roadmap stays in `claude-scratch-work` until Phase 9 ends. | Future agents must meet KISS before they write code | live |
| G-19 | **Lean-startup migration.** 9.1 builds a fully operational skeleton: every layer present but naive, run end to end by `tradingcrab` and one notebook, CI green. 9.2–9.8 each upgrade one module in place. Nothing is bulk-copied: each module is rewritten to the simplest version that meets its gate, using `claude-scratch-work` as reference and LEARNINGS.md as the guard. | Copying would carry the complexity over | live |
| G-20 | **One live decision log.** After the 9.1 merge, this `DECISIONS.md` (live rows only, same IDs) is the log to edit first; the `claude-scratch-work` copy keeps a banner pointing here, and Phase 9.2+ planning reads this copy. | Two editable logs would drift | live |
| G-21 | **Skeleton shape (9.1).** Flat modules in `trading_crab_lib/platform/`, one `argparse` CLI (`tradingcrab build`, `tradingcrab weekly`), pip-only install, no plotting yet, no registry or state tool until a first user needs them (CONTEXT D-08). | Readable in one sitting (P-07) | skeleton |
| G-22 | **Skeleton data (9.1).** FRED GS10, TB3MS, BAA and UNRATE plus Tiingo SPY, TLT, IAU and USO; complete month-ends only (the current month is dropped); UNRATE lag 1, the rest 0. `--allow-missing` is deferred to 9.2, when the sources that actually get blocked arrive. | Two keyed APIs that work on the VPN; the allocation needs every class | skeleton |
| G-23 | **Skeleton allocation (9.1).** Inverse-vol over the four ETFs on the last 36 month-end returns, scaled to a 10% vol target, the remainder in cash (clamped at 0). No backtest in 9.1: a truncation test shows the features are causal; the backtest, registry and first budgeted run arrive together in 9.4 (CONTEXT D-07). | Ten lines that exercise the point-in-time path without a performance number | skeleton |

Rows dropped because they narrated `claude-scratch-work`'s own history: G-03..G-05, G-07..G-10, G-12, G-13, L1-04, L2-05,
A-07, E-04. Read them in that repo.
