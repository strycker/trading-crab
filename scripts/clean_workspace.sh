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

# In a git checkout, note the tracked files already missing (the user's own deletions) before removing anything
git_ls_deleted() { git -c core.quotePath=false ls-files --deleted | sort; }
deleted_before=""
if [[ -e .git ]]; then
  deleted_before=$(git_ls_deleted)
fi

echo "clean_workspace: cleaning $root"
rm -rf data outputs dist dist-app dist-lib build src/trading_crab_lib/build .pytest_cache .ruff_cache

# Caches and build metadata anywhere below the root, except legacy/, .venv/ and .git/
find . \( -path ./legacy -o -path ./.venv -o -path ./.git \) -prune -o -type d \
  \( -name __pycache__ -o -name '*.egg-info' -o -name .ipynb_checkpoints -o -name .pytest_cache -o -name .ruff_cache \) \
  -prune -exec rm -rf {} +

# Fail loudly if this run removed a tracked file (it must never), naming only those files
if [[ -e .git ]]; then
  removed=$(comm -13 <(printf '%s\n' "$deleted_before") <(git_ls_deleted))
  if [[ -n "$removed" ]]; then
    echo "clean_workspace: this run removed tracked files:" >&2
    echo "$removed" >&2
    printf 'Restore exactly those with: git restore --' >&2
    while IFS= read -r path; do printf ' %q' "$path" >&2; done <<< "$removed"
    printf '\n' >&2
    exit 1
  fi
fi
echo "clean_workspace: done"
