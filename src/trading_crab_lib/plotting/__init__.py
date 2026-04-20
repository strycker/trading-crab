"""
plotting — Shared visualization helpers for all pipeline stages.

All plot functions:
  - Accept run_cfg: RunConfig and honour save_plots / show_plots
  - Save to outputs/plots/{step}_{description}.png when save_plots=True
  - Are importable by notebooks without side-effects

Custom 5-regime color palette (from legacy/unified_script.py):
    CUSTOM_COLORS = ["#0000d0","#d00000","#f48c06","#8338ec","#50a000"]

Submodules are added per Q-phase:
  Q1 → plotting/ingestion.py   (S1.8)
  Q2 → plotting/features.py    (S2.8)
  Q3 → plotting/clustering.py  (S3.9)
  Q4 → plotting/regime.py      (S4.3)
  Q5 → plotting/prediction.py  (S5.4)
  Q6 → plotting/assets.py      (S6.7)
  Q7 → plotting/diagnostics.py (S7.4)
"""

from __future__ import annotations

from trading_crab_lib.plotting.core import (
    CUSTOM_COLORS,
    PLOT_DIR,
    REGIME_CMAP,
    _in_jupyter,
    _plot_is_fresh,
    _regime_color,
    _save_or_show,
    list_available_plots,
    load_or_generate,
)

__all__ = [
    "CUSTOM_COLORS",
    "PLOT_DIR",
    "REGIME_CMAP",
    "load_or_generate",
    "list_available_plots",
]
