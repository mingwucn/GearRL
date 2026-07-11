#!/usr/bin/env python3
"""Persist frozen-design sensitivity to deterministic shaft offsets."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark.loader import FrozenBenchmarkLoader
from common.provenance import RunBundleStore
from evaluation.robustness import GeometricToleranceEvaluator
from synthesis.certified_graph import CertifiedSynthesisGraph


@dataclass(frozen=True)
class FrozenToleranceStudyConfig:
    """Immutable declaration of the signed shaft-offset sensitivity study."""

    sample_size: int = 120
    offsets_mm: tuple[float, ...] = (0.0, -0.1, -0.05, -0.01, 0.01, 0.05, 0.1)
    random_seed: int = 2026


class FrozenToleranceStudyRunner:
    """Evaluate selected certified trains and persist every perturbation result."""

    def __init__(self, output_root: Path):
        self._store = RunBundleStore(
            output_root,
            repository_root=Path(__file__).parent,
            environment_file=Path(__file__).parent / "environment-ai.yml",
        )
        self._evaluator = GeometricToleranceEvaluator()

    def run(self, dataset_root: Path, config: FrozenToleranceStudyConfig | None = None) -> Path:
        config = config or FrozenToleranceStudyConfig()
        if config.sample_size < 1 or not config.offsets_mm:
            raise ValueError("Tolerance sample size and offsets are required")
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        selected = [item for item in instances if item.expected_feasible][:config.sample_size]
        bundle, _ = self._store.create(
            random_seed=config.random_seed,
            dataset_id=dataset_id,
            dataset_hash=dataset_hash,
            config=asdict(config),
            model_version="certified-planar-v1",
        )
        counts = {offset: 0 for offset in config.offsets_mm}
        for instance in selected:
            graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
            solution = graph.solve()
            if solution is None:
                raise RuntimeError(f"Frozen feasible instance has no certified solution: {instance.instance_id}")
            for outcome in self._evaluator.evaluate(instance.problem, solution.train, config.offsets_mm):
                counts[outcome.offset_mm] += int(outcome.valid)
                identifier = f"{instance.instance_id}--offset-{outcome.offset_mm:+.6f}"
                self._store.write_result(bundle, identifier, {"instance_id": instance.instance_id, **asdict(outcome)})
        summary = {
            "instances": len(selected),
            "valid_rate_by_offset_mm": {str(offset): counts[offset] / len(selected) for offset in config.offsets_mm},
            "scope": "deterministic shaft-offset sensitivity under the exact mesh-center model",
        }
        (bundle / "tolerance_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--sample-size", type=int, default=120)
    args = parser.parse_args()
    print(FrozenToleranceStudyRunner(args.output_root).run(args.dataset, FrozenToleranceStudyConfig(sample_size=args.sample_size)))


if __name__ == "__main__":
    main()
