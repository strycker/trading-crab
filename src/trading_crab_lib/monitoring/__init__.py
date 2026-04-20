"""
monitoring — Pipeline monitoring helpers, validation summaries, diagnostic reports.

Submodules are added per Q-phase:
  Q1 → monitoring/ingestion.py  (S1.8) — validate_date_range, count_source_columns
  Q2 → monitoring/features.py   (S2.8) — compute_feature_quality
  Q3 → monitoring/clustering.py (S3.9) — compute_regime_stability
  Q5 → monitoring/prediction.py (S5.4) — compute_cv_fold_scores
  Q7 → monitoring/pipeline.py   (S7.5) — validate_step_output, PipelineHealthSummary
"""

from __future__ import annotations

__all__: list[str] = []
