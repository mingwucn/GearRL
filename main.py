"""Primary entry point for reproducible certified GearRL experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from run_certified_benchmark import CertifiedBenchmarkRunner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026, help="Benchmark generator seed")
    parser.add_argument("--count", type=int, default=100, help="Number of certified benchmark instances")
    parser.add_argument("--infeasible-count", type=int, default=0, help="Number of labeled infeasible benchmark instances")
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"), help="Immutable run-bundle root")
    parser.add_argument("--frozen-dataset", type=Path, help="Hash-verified frozen benchmark directory")
    args = parser.parse_args()
    runner = CertifiedBenchmarkRunner(args.output_root)
    bundle = runner.run_frozen(args.frozen_dataset) if args.frozen_dataset else runner.run(args.seed, args.count, args.infeasible_count)
    print(f"Certified benchmark bundle: {bundle}")


if __name__ == "__main__":
    main()
