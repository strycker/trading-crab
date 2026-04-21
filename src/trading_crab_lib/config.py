"""
Central config loader — call load() once at pipeline entry points.
Uses python-dotenv for secrets, PyYAML for settings.

Full implementation (validate_config, load_portfolio, setup_logging) added in S1.7.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from trading_crab_lib import CONFIG_DIR

log = logging.getLogger(__name__)


def load(
    settings_path: dict[str, Any] | Path | str | None = None,
) -> dict[str, Any]:
    """Load config and inject secrets from the environment.

    Args:
        settings_path: None → reads config/settings.yaml from repo root.
                       Path/str → reads from that file.
                       dict → uses the provided mapping directly (no file I/O).
    """
    load_dotenv()

    if isinstance(settings_path, dict):
        cfg: dict[str, Any] = settings_path
    else:
        path = (
            Path(settings_path)
            if settings_path is not None
            else CONFIG_DIR / "settings.yaml"
        )
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

    fred_key = os.getenv("FRED_API_KEY")
    if not fred_key:
        log.warning("FRED_API_KEY not set — FRED ingestion will fail")
    cfg.setdefault("fred", {})["api_key"] = fred_key

    return cfg
