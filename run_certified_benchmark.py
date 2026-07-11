#!/usr/bin/env python3
"""Run the certified deterministic baseline and write immutable raw results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from benchmark.generator import BenchmarkGenerator
from benchmark.loader import FrozenBenchmarkLoader
from common.provenance import RunBundleStore
from reporting.aggregate import ResultAggregator
from synthesis.certified_graph import CertifiedSynthesisGraph


class CertifiedBenchmarkRunner:
    """Orchestrate one immutable deterministic certified benchmark run."""

    def __init__(self, output_root: Path, generator: BenchmarkGenerator | None = None):
        self._generator = generator or BenchmarkGenerator()
        self._store = RunBundleStore(
            output_root,
            repository_root=Path(__file__).parent,
            environment_file=Path(__file__).parent / "environment-ai.yml",
        )

    def run(self, seed: int, count: int, infeasible_count: int = 0) -> Path:
        instances = self._generator.generate_suite(seed, count, infeasible_count)
        return self._run_instances(instances, seed, "compound-v1")

    def run_frozen(self, dataset_root: Path) -> Path:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        return self._run_instances(instances, 2026, dataset_id, dataset_hash)

    def _run_instances(self, instances, seed: int, dataset_id: str, dataset_hash: str | None = None) -> Path:
        bundle, _ = self._store.create(
            random_seed=seed,
            dataset_id=dataset_id,
            dataset_hash=dataset_hash or self._dataset_hash(instances),
            config={
                "method": "certified-branch-and-bound",
                "feasible_instance_count": sum(item.expected_feasible for item in instances),
                "infeasible_instance_count": sum(not item.expected_feasible for item in instances),
            },
            model_version="certified-planar-v1",
        )
        for instance in instances:
            started = perf_counter()
            result = CertifiedSynthesisGraph(
                instance.problem,
                instance.reference_train.stages,
                instance.reference_train.meshes,
            ).solve()
            elapsed = perf_counter() - started
            successful = result is not None
            self._store.write_result(
                bundle,
                instance.instance_id,
                {
                    "instance_id": instance.instance_id,
                    "valid": successful,
                    "expected_feasible": instance.expected_feasible,
                    "correct_classification": successful == instance.expected_feasible,
                    "runtime_s": elapsed,
                    "score": list(result.score) if result else None,
                    "certificate": result.certificate_json if result else None,
                },
            )
        ResultAggregator().write(bundle)
        return bundle

    @staticmethod
    def _dataset_hash(instances) -> str:
        payload = json.dumps([instance.to_json() for instance in instances], sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--infeasible-count", type=int, default=0)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--frozen-dataset", type=Path)
    args = parser.parse_args()
    runner = CertifiedBenchmarkRunner(args.output_root)
    print(runner.run_frozen(args.frozen_dataset) if args.frozen_dataset else runner.run(args.seed, args.count, args.infeasible_count))


if __name__ == "__main__":
    main()
