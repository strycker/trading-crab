"""
RunConfig — global runtime flags for the pipeline.

Mirrors the top-of-script flags in legacy/unified_script.py.
Construct one RunConfig at the entry point and pass it through every module.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass


@dataclass
class RunConfig:
    # ── verbosity ──────────────────────────────────────────────────────
    verbose: bool = False

    # ── plotting ───────────────────────────────────────────────────────
    generate_plots: bool = False
    generate_pairplot: bool = False
    generate_scatter_matrix: bool = False
    save_plots: bool = True
    show_plots: bool = False

    # ── data refresh ───────────────────────────────────────────────────
    refresh_source_datasets: bool = False
    recompute_derived_datasets: bool = False
    refresh_asset_prices: bool = False
    refresh_preservation_checkpoints: bool = False

    # ── misc ───────────────────────────────────────────────────────────
    use_constrained_kmeans: bool = True
    drop_incomplete_tail: bool = True
    market_code_source: str | None = None

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RunConfig":
        """Build a RunConfig from a parsed argparse.Namespace."""
        return cls(
            verbose=getattr(args, "verbose", False),
            generate_plots=getattr(args, "plots", False),
            generate_pairplot=getattr(args, "pairplot", False),
            generate_scatter_matrix=getattr(args, "scatter_matrix", False),
            save_plots=not getattr(args, "no_save_plots", False),
            show_plots=getattr(args, "show_plots", False),
            refresh_source_datasets=getattr(args, "refresh", False),
            recompute_derived_datasets=getattr(args, "recompute", False),
            refresh_asset_prices=getattr(args, "refresh_assets", False),
            refresh_preservation_checkpoints=getattr(args, "refresh_preservation", False),
            use_constrained_kmeans=not getattr(args, "no_constrained", False),
            market_code_source=getattr(args, "market_code", None),
            drop_incomplete_tail=not getattr(args, "no_drop_tail", False),
        )

    def apply_logging(self) -> None:
        """Set root logger to DEBUG if verbose, else leave at INFO."""
        if self.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    def __str__(self) -> str:
        flags = []
        if self.verbose:            flags.append("verbose")
        if self.generate_plots:     flags.append("plots")
        if self.generate_pairplot:  flags.append("pairplot")
        if self.refresh_source_datasets:    flags.append("refresh")
        if self.recompute_derived_datasets: flags.append("recompute")
        if self.refresh_asset_prices:       flags.append("refresh-assets")
        if self.refresh_preservation_checkpoints: flags.append("refresh-preservation")
        if self.market_code_source: flags.append(f"market_code={self.market_code_source}")
        return f"RunConfig({', '.join(flags) or 'defaults'})"

