.PHONY: help setup setup-dev install install-dev test test-fast run run-full \
	run-cluster dashboard notebooks clean-outputs clean-models clean-all \
	ruff lint fmt build all

help:
	@echo ""
	@echo "Trading-Crab — available make targets"
	@echo "--------------------------------------"
	@echo "  make setup          Set up .venv + install runtime deps (interactive)"
	@echo "  make setup-dev      Set up .venv + install dev deps (tests + notebooks)"
	@echo "  make install        pip install both packages into active env"
	@echo "  make install-dev    pip install both packages + dev extras"
	@echo ""
	@echo "  make test           Run the full test suite"
	@echo "  make test-fast      Run tests, stop at first failure"
	@echo ""
	@echo "  make run            Steps 3-7 from cached data (fast, no re-scraping)"
	@echo "  make run-full       Full pipeline — re-scrape + recompute + plots"
	@echo "  make run-cluster    Re-cluster only (step 3) with plots"
	@echo "  make dashboard      Print current dashboard (step 7 only)"
	@echo "  make notebooks      Launch JupyterLab"
	@echo ""
	@echo "  make clean-outputs  Remove generated plots and reports"
	@echo "  make clean-models   Remove saved models"
	@echo "  make clean-all      Remove all generated files (keep raw checkpoints)"
	@echo ""
	@echo "  make ruff           Run ruff lint checks (src + tests)"
	@echo "  make lint           Alias for ruff checks"
	@echo "  make fmt            Auto-fix + format with ruff"
	@echo "  make build          Build app + lib dists into ./dist"
	@echo "  make all            Run lint + tests + build"
	@echo ""

# ── setup ──────────────────────────────────────────────────────────────────────

setup:
	bash scripts/setup.sh

setup-dev:
	bash scripts/setup.sh --dev

install:
	pip install -e "src/trading_crab_lib/[all]"
	pip install -e "."

install-dev:
	pip install -e "src/trading_crab_lib/[all,dev]"
	pip install -e ".[dev]"
	pip install ruff build

# ── testing ────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-fast:
	pytest tests/ -x -q

# ── lint / format / build ─────────────────────────────────────────────────────

ruff:
	ruff check src tests

lint: ruff

fmt:
	ruff check src tests --fix
	ruff format src tests

build:
	python -m pip install --upgrade pip
	python -m pip install build
	python -m build . --outdir dist
	python -m build ./src/trading_crab_lib --outdir dist

all: lint test build

# ── pipeline ───────────────────────────────────────────────────────────────────

run:
	python run_pipeline.py --steps 3,4,5,6,7 --plots

run-full:
	python run_pipeline.py --refresh --recompute --plots --save-market-code

run-cluster:
	python run_pipeline.py --steps 3,4 --plots --recompute

dashboard:
	python pipelines/07_dashboard.py

notebooks:
	jupyter lab notebooks/

# ── cleanup ────────────────────────────────────────────────────────────────────

clean-outputs:
	rm -f outputs/plots/*.png outputs/plots/*.pdf
	rm -f outputs/reports/*.csv outputs/reports/*.md

clean-models:
	rm -f outputs/models/*.pkl outputs/models/*.joblib

clean-all: clean-outputs clean-models
	rm -f data/processed/*.parquet
	rm -f data/regimes/*.parquet
	@echo "Kept data/raw/ and data/checkpoints/ — run 'make run' to regenerate"
