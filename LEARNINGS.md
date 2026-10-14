# Learnings: mistakes not to repeat

One line each: the mistake → the rule that prevents it [source]. Sources: the legacy pitfalls P1–P27, the
`claude-scratch-work` rebuild guide ("Learnings from 8.1–8.5"), DECISIONS rows and the 9.1 research. Read this before
writing a module; add a line when a new mistake teaches a rule.

## Look-ahead and point-in-time

1. Centred rolling windows in a supervised feature leaked the future → causal features only: trailing windows, no `center=True`, no `shift(-k)`, no backfill; prove it with a truncation test [P1, L2-04].
2. Three series (`m2sl`, `totalsl`, `div_yield`) entered features at their reference month for seven phases → every raw series has a `publication_lags` entry, applied once at ingestion; an unlisted column fails the build [D-05].
3. A lag applied in config and again in a table doubled the shift → one place for lags; nothing re-applies them after ingestion [publication_lags.py].
4. Lowering a lag silently reopens look-ahead → an independent floor test per lag, not read from the config under test [08.1].
5. Monthly-average prices in P&L carried an intra-month move → P&L on month-end prices; averages are model inputs only [E-07, E-08].
6. Vol estimated on average prices ran 13–17% low → estimate vol on month-end returns [E-11].
7. Features and labels aligned by `iloc` mis-shifted silently → align on the index intersection [P3, P5].
8. Shuffled CV and `train_test_split` on time series leaked → walk-forward or purged splits only [P4, H-04].

## Data and builds

9. A failed fetch fell back to IAU and a −98% gold return shipped with no error → a failed source fails the build before any write, naming every failure [D-08, P23].
10. Merge-on-save refilled derived columns from a stale disk copy → every save overwrites whole; no merge [D-08].
11. A fallback in a different price scale spliced silently → a fallback is a failure unless explicitly allowed; log the resolved source [D-08].
12. Wall-clock freshness called stale data fresh → record the data end date and judge staleness against each series' publication lag [P13, A-12].
13. A hardcoded `end_date` silently ignored new data → `null` means today [P12].
14. Sources behind bot checks failed on the VPN → prefer keyed REST APIs and plain files; a source that needs a browser is not a dependency [08.4/08.5 gate logs].
15. Keys leaked through exception text → keys come only from the environment, never in logs or notebook output; FRED's key rides the URL, so redact it from every exception [T-06-01].

## Tests and tracked files

16. Record-pin tests tied to tracked data went stale at every rebuild → no test reads tracked data; synthetic fixtures; a `realdata` marker for built data [08.5, G-14].
17. Tracked data and pickles caused stale-data bugs → nothing generated in git; `.gitignore` by path from the first commit; a hygiene test [P25, G-14].
18. Pickles execute code on load → Parquet and JSON only; refit locally; no new pickle through git [P27].
19. Tests wrote production checkpoints → every test runs under `TC_ROOT_DIR=tmp_path`; operator env overrides never leak into tests [P20, 08.4 UAT].
20. The live path was never run on real data; every weekly test used a fake model → a real data → page smoke exists from the first milestone [guide §1.4].
21. A constant model passed unnoticed (one posterior for 231 months) → count distinct outputs after any fit [guide §1.5, A-08].
22. Regime ids were renumbered by every refit → alignment is part of the labeler's API [guide §1.6, L1-06].
23. Bit-exact float assertions broke across macOS and Linux → rel 1e-9, abs 0 [H-10].
24. A check that could only confirm hid defects → core invariants ship with a mutation that turns the test red [H-11].

## Scope and process

25. Building inside the legacy package left 31 import sites → this repo imports nothing legacy; a hygiene test checks it [guide §1.8].
26. Notebooks written after the fact lagged three phases → each module ships its notebook and a sign-off cell [guide §1.9, G-01].
27. Honesty ceremony arrived before any candidate existed → registry, DSR and mutation proofs only for decision-bearing numbers [guide §1.10, P-07].
28. The regime layer never beat its own no-regime ablation, yet machinery grew around it → build the baseline and scoreboard first; regime work is gated on beating the ablation [E-06, E-12, G-06].
29. Planning grew to 5.5 times the code changed → at most 3 plans of about 150 lines; decisions are rows [G-03].
30. Bulk-copied complexity persists → rewrite each module from the architecture; old code is reference only [G-19].
31. Option and config sprawl → a new switch needs a reason a reader can state in one line [P-07].
32. Verification layers on non-decision numbers → rigor only where a number drives a decision [P-07].
33. Re-running the budgeted backtest to refresh a page spent registry rows → pages never trigger an evaluation [honesty rules].
34. A run on the wrong branch looked like a result → every run prints `Code: <branch> @ <sha>` first [G-16].

## Packaging and release

35. `python -m build` exited 0 and shipped an empty library wheel for five releases → list packages by name; CI installs the built wheels in a fresh venv and imports them from site-packages [RELEASING §9, 9.1 research].
36. A broad `.gitignore` pattern (`*checkpoint*`) can swallow a source file → ignore by path (`/data/`, `/outputs/`); test that every source file is tracked [9.1 research].
37. Two workflows and two publish triggers for one package double-published → one workflow per concern, one trigger per package; a published version number is burned forever, so verify the installed artifact before tagging [L5, L11, RELEASING §3].
38. `import platform` resolves to this repo's `platform/` package when Python runs from `src/trading_crab_lib/` → never run Python, pytest or notebooks with that working directory [9.1 research, Pitfall 4].

## Secrets in tests

39. A fake API key in a test tripped GitGuardian's high-entropy detector → fake keys are low-entropy `fake-...` values on lines marked `# ggignore` [GitGuardian incident 2026-10-14].
