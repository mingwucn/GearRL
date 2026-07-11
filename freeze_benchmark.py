#!/usr/bin/env python3
"""Freeze the certified GearRL benchmark into a dataset directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark.freeze import BenchmarkFreezer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--feasible-count", type=int, default=300)
    parser.add_argument("--infeasible-count", type=int, default=100)
    args = parser.parse_args()
    print(BenchmarkFreezer().freeze(args.output, args.seed, args.feasible_count, args.infeasible_count))


if __name__ == "__main__":
    main()
