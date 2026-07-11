#!/usr/bin/env python3
"""Persist a backlash-versus-center-expansion response surface."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark.loader import FrozenBenchmarkLoader
from common.provenance import RunBundleStore
from evaluation.backlash import BacklashRobustnessEvaluator
from synthesis.certified_graph import CertifiedSynthesisGraph


@dataclass(frozen=True)
class BacklashStudyConfig:
    sample_size: int = 120
    allowances_mm: tuple[float, ...] = (0.0, 0.01, 0.05, 0.1)
    expansions_mm: tuple[float, ...] = (0.0, 0.01, 0.05, 0.1)
    random_seed: int = 2026


class FrozenBacklashStudyRunner:
    """Persist every frozen-layout point in the declared backlash surface."""

    def __init__(self, output_root: Path):
        self._store = RunBundleStore(output_root, repository_root=Path(__file__).parent, environment_file=Path(__file__).parent / "environment-ai.yml")
        self._evaluator = BacklashRobustnessEvaluator()

    def run(self, dataset_root: Path, config: BacklashStudyConfig | None = None) -> Path:
        config = config or BacklashStudyConfig()
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        selected = [item for item in instances if item.expected_feasible][:config.sample_size]
        bundle, _ = self._store.create(random_seed=config.random_seed, dataset_id=dataset_id, dataset_hash=dataset_hash, config=asdict(config), model_version="certified-planar-backlash-v1")
        counts = {(allowance, expansion): 0 for allowance in config.allowances_mm for expansion in config.expansions_mm}
        for instance in selected:
            solution = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes).solve()
            if solution is None:
                raise RuntimeError(f"Frozen feasible instance has no solution: {instance.instance_id}")
            for outcome in self._evaluator.evaluate(instance.problem, solution.train, config.allowances_mm, config.expansions_mm):
                key = (outcome.transverse_backlash_allowance_mm, outcome.center_expansion_per_mesh_mm)
                counts[key] += int(outcome.valid)
                identifier = f"{instance.instance_id}--backlash-{key[0]:.6f}--expansion-{key[1]:.6f}"
                self._store.write_result(bundle, identifier, {"instance_id": instance.instance_id, **asdict(outcome)})
        surface = {f"allowance={allowance},expansion={expansion}": counts[(allowance, expansion)] / len(selected) for allowance in config.allowances_mm for expansion in config.expansions_mm}
        (bundle / "backlash_summary.json").write_text(json.dumps({"instances": len(selected), "valid_rate_surface": surface}, indent=2, sort_keys=True) + "\n")
        return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
    args = parser.parse_args()
    print(FrozenBacklashStudyRunner(args.output_root).run(args.dataset))


if __name__ == "__main__":
    main()
