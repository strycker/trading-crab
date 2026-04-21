"""
Checkpoint persistence helpers for pipeline intermediate datasets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from trading_crab_lib import DATA_DIR

CHECKPOINT_DIR = DATA_DIR / "checkpoints"


class CheckpointManager:
    """Simple DataFrame checkpoint reader/writer using parquet format."""

    def __init__(self, checkpoint_dir: Path | None = None):
        self.checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _data_path(self, name: str) -> Path:
        return self.checkpoint_dir / f"{name}.parquet"

    def _meta_path(self, name: str) -> Path:
        return self.checkpoint_dir / f"{name}.meta.json"

    def save(
        self, df: pd.DataFrame, name: str, metadata: dict[str, Any] | None = None
    ) -> Path:
        """Persist *df* under *name* and write a lightweight metadata sidecar."""
        data_path = self._data_path(name)
        meta_path = self._meta_path(name)
        df.to_parquet(data_path)

        payload: dict[str, Any] = {"created": datetime.now(timezone.utc).isoformat()}
        if metadata:
            payload["metadata"] = metadata
        meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return data_path

    def load(self, name: str) -> pd.DataFrame:
        """Load a previously saved dataframe checkpoint by *name*."""
        data_path = self._data_path(name)
        if not data_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {data_path}")
        return pd.read_parquet(data_path)
