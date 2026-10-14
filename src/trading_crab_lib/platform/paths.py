"""Where the checkout lives: ``root()``, ``data_dir()``, ``outputs_dir()``, ``config_path()``.

``root()`` is ``$TC_ROOT_DIR`` when set, else the nearest folder at or above the current directory that holds
``config/platform_settings.yaml``. Every function resolves on each call, never at import time, so an installed
wheel and each test (``TC_ROOT_DIR=tmp_path``) find the right tree.

Usage::

    from trading_crab_lib.platform.paths import data_dir
    data_dir() / "checkpoints"
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_RELPATH = Path("config") / "platform_settings.yaml"


def root() -> Path:
    """The checkout root: ``$TC_ROOT_DIR``, else the cwd walk; raises FileNotFoundError naming the fix."""
    env = os.environ.get("TC_ROOT_DIR")
    if env:
        return Path(env)
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / CONFIG_RELPATH).is_file():
            return folder
    raise FileNotFoundError(
        f"no {CONFIG_RELPATH} at or above {here}: run inside the trading-crab checkout or set TC_ROOT_DIR to it"
    )


def config_path() -> Path:
    """The one settings file."""
    return root() / CONFIG_RELPATH


def data_dir() -> Path:
    """Generated data (ignored by git): checkpoints and the holdout."""
    return root() / "data"


def outputs_dir() -> Path:
    """Generated outputs (ignored by git): the weekly page."""
    return root() / "outputs"
