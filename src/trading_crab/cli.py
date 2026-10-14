"""The ``tradingcrab`` front door (D-04): ``build``, ``weekly``, ``--version``, ``--help``.

The code line is printed before anything else, argument parsing included, so ``--help`` and usage errors show
it too (G-16).

Usage::

    tradingcrab build     # build monthly_raw behind the holdout fence
    tradingcrab weekly    # write outputs/reports/weekly_report.md from the built data
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from trading_crab_lib.platform import ingest, report
from trading_crab_lib.platform.code_version import code_version
from trading_crab_lib.platform.config import ConfigError, load


def _versions() -> str:
    """Installed versions of both packages, from their metadata."""
    found = []
    for dist in ("trading-crab", "trading-crab-lib"):
        try:
            found.append(f"{dist} {version(dist)}")
        except PackageNotFoundError:
            found.append(f"{dist} (not installed)")
    return ", ".join(found)


def _build() -> int:
    raw = ingest.build(load())
    print(f"Built monthly_raw: {len(raw)} rows, data through month-end {raw.index.max():%Y-%m-%d}")
    return 0


def _weekly() -> int:
    print(f"Weekly page: {report.run(load())}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand; return 0, or 1 with an ``ERROR:`` line on stderr that names the fix."""
    print(code_version(), flush=True)
    parser = argparse.ArgumentParser(prog="tradingcrab", description="Trading-Crab: weekly, guidance-only portfolio advice.")
    parser.add_argument("--version", action="version", version=_versions())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="build the monthly data (monthly_raw) behind the holdout fence")
    sub.add_parser("weekly", help="write outputs/reports/weekly_report.md from the built data")
    args = parser.parse_args(argv)
    try:
        return {"build": _build, "weekly": _weekly}[args.command]()
    except (ingest.BuildFailed, ConfigError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
