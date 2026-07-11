#!/usr/bin/env python3
"""Persist a stratified static-strength screening study on frozen designs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark.loader import FrozenBenchmarkLoader
from common.design_models import MaterialLoadCase
from common.provenance import RunBundleStore
from evaluation.cae_study import StratifiedCAEStudy


@dataclass(frozen=True)
class FrozenCAEStudyConfig:
    """Immutable declaration of the digital static-strength experiment."""

    sample_size: int = 120
    minimum_safety_factor: float = 1.0
    random_seed: int = 2026


class FrozenCAEStudyRunner:
    """Run declared CAE screening and retain immutable per-layout evidence."""

    def __init__(self, output_root: Path):
        self._store = RunBundleStore(
            output_root,
            repository_root=Path(__file__).parent,
            environment_file=Path(__file__).parent / "environment-ai.yml",
        )

    def run(self, dataset_root: Path, config: FrozenCAEStudyConfig | None = None) -> Path:
        config = config or FrozenCAEStudyConfig()
        if config.sample_size < 1 or config.minimum_safety_factor <= 0:
            raise ValueError("CAE sample size and minimum safety factor must be positive")
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        load_case = MaterialLoadCase("steel", 1.0, 10.0, 210_000.0, 0.3, 800.0)
        outcomes = StratifiedCAEStudy(load_case, config.minimum_safety_factor).evaluate(instances, config.sample_size)
        bundle, _ = self._store.create(
            random_seed=config.random_seed,
            dataset_id=dataset_id,
            dataset_hash=dataset_hash,
            config={**asdict(config), "load_case": asdict(load_case)},
            model_version="certified-planar-v1",
        )
        for outcome in outcomes:
            self._store.write_result(bundle, outcome.instance_id, asdict(outcome))
        safety = [item.minimum_safety_factor for item in outcomes if item.minimum_safety_factor is not None]
        summary = {
            "observations": len(outcomes),
            "valid_count": sum(item.valid for item in outcomes),
            "minimum_safety_factor": min(safety) if safety else None,
        }
        (bundle / "cae_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--sample-size", type=int, default=120)
    args = parser.parse_args()
    print(FrozenCAEStudyRunner(args.output_root).run(args.dataset, FrozenCAEStudyConfig(sample_size=args.sample_size)))


if __name__ == "__main__":
    main()
