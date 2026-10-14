"""Load ``config/platform_settings.yaml``, fail fast on every missing section at once, add the API keys.

Keys never live in the YAML: ``FRED_API_KEY`` and ``TIINGO_API_KEY`` come from the environment, or from
``<root>/.env`` (an exported variable wins over ``.env``). A missing key is ``None`` here; the build refuses
to run without it. Show a config with ``redacted(cfg)``, never ``print(cfg)``.

Usage::

    from trading_crab_lib.platform.config import load, redacted
    cfg = load()                   # or load({...}) in a test, or load(Path("other.yaml"))
    cfg["holdout"]["cutoff"]       # "2020-12-31"
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from trading_crab_lib.platform.paths import config_path, root

REQUIRED_SECTIONS = ("data", "fred", "tickers", "publication_lags", "holdout", "allocation", "report")
KEY_NAMES = ("FRED_API_KEY", "TIINGO_API_KEY")


class ConfigError(ValueError):
    """The settings are incomplete or malformed; the message lists every problem at once."""


def load(source: dict[str, Any] | Path | None = None) -> dict[str, Any]:
    """The validated settings plus ``cfg["keys"]`` ({key name: value or None}); the input is not changed."""
    if isinstance(source, dict):
        cfg = dict(source)
    else:
        path = Path(source) if source is not None else config_path()
        if not path.is_file():
            raise FileNotFoundError(f"{path} not found: run inside the trading-crab checkout or set TC_ROOT_DIR to it")
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(cfg, dict):
            raise ConfigError(f"{path}: the top level must be a mapping of sections")
    errors = [f"missing required section '{name}'" for name in REQUIRED_SECTIONS if name not in cfg]
    if errors:
        raise ConfigError(f"platform settings have {len(errors)} error(s):\n" + "\n".join(f"  - {e}" for e in errors))
    load_dotenv(root() / ".env")  # never overrides a variable that is already exported
    cfg["keys"] = {name: os.environ.get(name) or None for name in KEY_NAMES}
    return cfg


def redacted(cfg: dict[str, Any]) -> dict[str, Any]:
    """A copy safe to print: every key value replaced by ``***`` (``None`` stays ``None``)."""
    return {**cfg, "keys": {name: "***" if value else None for name, value in cfg.get("keys", {}).items()}}
