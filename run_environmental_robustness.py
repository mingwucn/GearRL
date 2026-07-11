#!/usr/bin/env python3
"""Persist frozen housing-clearance and static-load robustness evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark.loader import FrozenBenchmarkLoader
from common.design_models import MaterialLoadCase
from common.provenance import RunBundleStore
from evaluation.environmental_robustness import EnvironmentalRobustnessEvaluator
from synthesis.certified_graph import CertifiedSynthesisGraph
from cae.qualification import StaticStrengthAdmissionPolicy


@dataclass(frozen=True)
class EnvironmentalRobustnessConfig:
    sample_size: int = 120
    housing_erosions_mm: tuple[float, ...] = (0.0, 0.1, 0.5, 1.0, 5.0)
    load_multipliers: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0)
    minimum_safety_factor: float = 1.0
    random_seed: int = 2026


class FrozenEnvironmentalRobustnessRunner:
    """Persist all declared housing and load perturbation outcomes."""

    def __init__(self, output_root: Path):
        self._store = RunBundleStore(output_root, repository_root=Path(__file__).parent, environment_file=Path(__file__).parent / "environment-ai.yml")
        self._evaluator = EnvironmentalRobustnessEvaluator()

    def run(self, dataset_root: Path, config: EnvironmentalRobustnessConfig | None = None) -> Path:
        config = config or EnvironmentalRobustnessConfig()
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        selected = [item for item in instances if item.expected_feasible][:config.sample_size]
        load_case = MaterialLoadCase("steel", 1.0, 10.0, 210_000.0, 0.3, 800.0)
        bundle, _ = self._store.create(random_seed=config.random_seed, dataset_id=dataset_id, dataset_hash=dataset_hash, config={**asdict(config), "load_case": asdict(load_case)}, model_version="certified-planar-v1")
        housing_counts = {value: 0 for value in config.housing_erosions_mm}
        load_counts = {value: 0 for value in config.load_multipliers}
        load_safety: dict[float, list[float]] = {value: [] for value in config.load_multipliers}
        for instance in selected:
            solution = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes).solve()
            if solution is None:
                raise RuntimeError(f"Frozen feasible instance has no solution: {instance.instance_id}")
            for outcome in self._evaluator.evaluate_housing(instance, solution.train, config.housing_erosions_mm):
                housing_counts[outcome.clearance_erosion_mm] += int(outcome.valid)
                self._store.write_result(bundle, f"housing--{instance.instance_id}--{outcome.clearance_erosion_mm:.6f}", {"study": "housing", **asdict(outcome)})
            for outcome in self._evaluator.evaluate_load(instance, solution.train, load_case, config.load_multipliers, config.minimum_safety_factor):
                load_counts[outcome.load_multiplier] += int(outcome.valid)
                if outcome.minimum_safety_factor is not None:
                    load_safety[outcome.load_multiplier].append(outcome.minimum_safety_factor)
                self._store.write_result(bundle, f"load--{instance.instance_id}--{outcome.load_multiplier:.6f}", {"study": "load", **asdict(outcome)})
        summary = {
            "instances": len(selected),
            "housing_valid_rate": {str(value): housing_counts[value] / len(selected) for value in config.housing_erosions_mm},
            "load_valid_rate": {str(value): load_counts[value] / len(selected) for value in config.load_multipliers},
            "minimum_safety_factor_by_load": {str(value): min(load_safety[value]) for value in config.load_multipliers},
            "load_admission_qualified": StaticStrengthAdmissionPolicy().qualification().qualified,
        }
        (bundle / "environmental_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
    args = parser.parse_args()
    print(FrozenEnvironmentalRobustnessRunner(args.output_root).run(args.dataset))


if __name__ == "__main__":
    main()
