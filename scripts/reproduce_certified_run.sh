#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

conda run -n ai pytest -q
conda run -n ai python main.py --seed 2026 --count 300 --infeasible-count 100 --output-root artifacts/runs
