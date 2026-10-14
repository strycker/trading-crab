#!/usr/bin/env bash
# Remove everything generated: data/, outputs/, builds and caches. Never touches a tracked file,
# legacy/ (frozen, CONTEXT D-14), .env or .venv/.
# Usage (from anywhere): bash scripts/clean_workspace.sh
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
if [[ ! -f pyproject.toml || ! -d src/trading_crab_lib/platform ]]; then
  echo "clean_workspace: $root is not a trading-crab checkout (no pyproject.toml or src/trading_crab_lib/platform/); nothing removed" >&2
  exit 1
fi

echo "clean_workspace: cleaning $root"
rm -rf data outputs dist dist-app dist-lib build src/trading_crab_lib/build .pytest_cache .ruff_cache

# Caches and build metadata anywhere below the root, except legacy/, .venv/ and .git/
find . \( -path ./legacy -o -path ./.venv -o -path ./.git \) -prune -o -type d \
  \( -name __pycache__ -o -name '*.egg-info' -o -name .ipynb_checkpoints -o -name .pytest_cache -o -name .ruff_cache \) \
  -prune -exec rm -rf {} +

# In a git checkout, fail loudly if any tracked file is missing (this script must never cause that)
if [[ -e .git ]]; then
  missing=$(git ls-files --deleted)
  if [[ -n "$missing" ]]; then
    echo "clean_workspace: tracked files are missing from the working tree:" >&2
    echo "$missing" >&2
    echo "Run: git restore ." >&2
    exit 1
  fi
fi
echo "clean_workspace: done"
