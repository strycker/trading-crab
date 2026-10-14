# Module map (M0–M8, M9+)

Each module with its phase, its interface, the naive version in the 9.1 skeleton, its target and its gate. Paths are
relative to `src/trading_crab_lib/platform/`. The decisions behind each row are in `DECISIONS.md`.

| # | Module | Phase | Interface | Skeleton (naive, 9.1) | Target | Gate |
|---|---|---|---|---|---|---|
| M0 | Skeleton | 9.1 | config, paths, code line, checkpoints, CLI, CI | `paths.py`, `config.py`, `code_version.py`, `checkpoints.py`; `tradingcrab` (argparse); CI with the wheel smoke | adds the state tool and the registry when first used (G-15) | `tradingcrab --help` prints the code line; both wheels import from site-packages; CI green |
| M1 | Data spine | 9.2 | sources → `monthly_raw`, publication lags applied, holdout fenced | `ingest.py`: 4 FRED + 4 Tiingo series, lags, fence, fail-loud (G-22) | ALFRED vintages, splices to 1962, World Bank gold, `--allow-missing`, walk-forward runner, coverage plot | point-in-time test; fail-loud test; coverage plot |
| M2 | Features | 9.3 | `monthly_raw` → causal features | `features.py`: 5 causal columns, a backdrop that gates no weight | the lean named taxonomy (D-06) with its notebook | truncation test; taxonomy table |
| M3 | Allocator + backtest | 9.4 | month-end returns → weights → walk-forward curve | `allocate.py`: inverse-vol, 10% vol target, cash remainder; no backtest (G-23) | vol-targeted core, walk-forward vs SPY, 60/40 and Faber, costs, DSR, registry | scoreboard renders; costs applied; registry rows within budget |
| M4 | Weekly report | 9.5 | data + weights (+ holdings) → Markdown page | `report.py`: code line, as-of dates, STALE banner, weights, backdrop | holdings, no-trade band, tripwire, run 2 equals run 3 | page renders from a real build with its as-of dates |
| M5 | Regime labeler | 9.6 | features → states and profiles, aligned across refits | none | jump model (L1-01..L1-06) | timeline vs recessions; occupancy; profiles make sense |
| M6 | Nowcaster + filter | 9.7 | causal features → P(regime now) → filtered belief | none | calibrated logistic plus Bayes filter (L2-01..L2-04) | distinct-output count above 1; truncation test |
| M7 | Regime tilt + ablation | 9.8 | belief → tilted weights, compared with the ablation | none | tilt with its no-regime ablation leg (G-06) | tilt beats the ablation net of costs, or it stays advisory |
| M8 | Honesty | with its first user | fence, walk-forward, registry, budgets, DSR | the holdout fence only (`checkpoints.py`, H-01) | walk-forward with M1 (9.2); registry, budgets and DSR with M3 (9.4) | DSR computed against the registry |
| M9+ | Hysteresis, stability, second classifier, mixture of experts, tactics | backlog | as designed | none | per module (A-03) | per module |

Every gate also needs the module's `realdata` tests green on Glenn's Mac after a `tradingcrab build`.
MVP-1 (a usable product with no regime model) is M0–M4; MVP-2 (regime-aware) adds M5–M7.
