#!/usr/bin/env bash
# Install both built wheels into a fresh venv and import them from site-packages.
# An empty wheel passes build, twine and version checks (the 0.1.x incident); only install-and-import catches it.
# Usage: bash scripts/check_wheels.sh dist-lib dist-app
set -euo pipefail
lib_dist=$(cd "$1" && pwd)
app_dist=$(cd "$2" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
"${PYTHON:-python3}" -m venv "$tmp/venv"
"$tmp/venv/bin/pip" install --quiet "$lib_dist"/*.whl "$app_dist"/*.whl   # one command: the app pins lib>=0.2.0
cd "$tmp"   # leave the checkout, or the repo itself would satisfy the imports
"$tmp/venv/bin/python" -I - "$app_dist" <<'PY'
import glob, sys, zipfile
import trading_crab, trading_crab_lib.platform as platform_pkg
for mod in (trading_crab, platform_pkg):
    assert "site-packages" in mod.__file__, f"{mod.__name__} imported from {mod.__file__}, not the installed wheel"
wheel = zipfile.ZipFile(glob.glob(sys.argv[1] + "/*.whl")[0])
meta = wheel.read(next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))).decode()
assert "Requires-Dist: trading-crab-lib" in meta, "the app wheel does not require trading-crab-lib"
print("check_wheels: both wheels install and import from site-packages; the app requires the lib")
PY
