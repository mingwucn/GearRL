#!/usr/bin/env python3
"""Create an immutable paired learned-policy efficiency experiment bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch

from benchmark.generator import BenchmarkGenerator, BenchmarkInstance
from common.provenance import RunBundleStore
from evaluation.paired_efficiency import PairedEfficiencyStudy
from synthesis.baselines import BranchAndBoundSolver
from synthesis.certified_environment import CertifiedBranchOrderingEnvironment
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import (
    BranchOrderingImitationTrainer,
    CertifiedDemonstrationCollector,
    DemonstrationBatch,
    LearnedBranchOrderingPolicy,
    PPOBranchRefinementTrainer,
)


@dataclass(frozen=True)
class PairedPolicyStudyConfig:
    """Immutable configuration for one preregistered-style policy study."""

    seed: int
    train_instances: int
    test_instances: int
    imitation_epochs: int = 100
    timing_repetitions: int = 5
    bootstrap_samples: int = 5_000


class PairedPolicyStudyRunner:
    """Train, evaluate, and persist a masked policy without hand-authored metrics."""

    def __init__(self, output_root: Path, generator: BenchmarkGenerator | None = None):
        self._generator = generator or BenchmarkGenerator()
        self._store = RunBundleStore(
            output_root,
            repository_root=Path(__file__).parent,
            environment_file=Path(__file__).parent / "environment-ai.yml",
        )

    def run(self, config: PairedPolicyStudyConfig) -> Path:
        self._validate(config)
        torch.manual_seed(config.seed)
        train_instances = self._generator.generate_compound_instances(config.seed, config.train_instances)
        test_instances = self._generator.generate_compound_instances(config.seed + 10_000, config.test_instances)
        policy = self._train_policy(train_instances, config.imitation_epochs)
        study = PairedEfficiencyStudy(
            BranchAndBoundSolver(),
            max_actions=policy.max_actions,
            timing_repetitions=config.timing_repetitions,
            bootstrap_samples=config.bootstrap_samples,
            bootstrap_seed=config.seed,
        )
        outcomes = study.evaluate(policy, test_instances)
        summary = study.summarize(outcomes)
        bundle, _ = self._store.create(
            random_seed=config.seed,
            dataset_id="compound-v1-paired-policy-test",
            dataset_hash=self._dataset_hash(test_instances),
            config=asdict(config),
            model_version="masked-certified-branch-ordering-v1",
        )
        torch.save(policy.network.state_dict(), bundle / "policy_state.pt")
        by_id = {instance.instance_id: instance for instance in test_instances}
        for outcome in outcomes:
            instance = by_id[outcome.instance_id]
            self._store.write_result(bundle, outcome.instance_id, self._record(instance, outcome))
        (bundle / "paired_summary.json").write_text(json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n")
        return bundle

    def _train_policy(self, instances: list[BenchmarkInstance], epochs: int) -> LearnedBranchOrderingPolicy:
        policy = LearnedBranchOrderingPolicy(max_actions=3)
        collector = CertifiedDemonstrationCollector()
        batches = [
            collector.collect(CertifiedSynthesisGraph(item.problem, item.reference_train.stages, item.reference_train.meshes), policy.max_actions)
            for item in instances
        ]
        batch = DemonstrationBatch(
            np.concatenate([item.features for item in batches]),
            np.concatenate([item.action_indices for item in batches]),
        )
        BranchOrderingImitationTrainer(policy).train(batch, epochs=epochs)
        refiner = PPOBranchRefinementTrainer(policy)
        for instance in instances:
            graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
            refiner.refine_episode(CertifiedBranchOrderingEnvironment(graph, policy.max_actions))
        return policy

    @staticmethod
    def _record(instance: BenchmarkInstance, outcome) -> dict:
        return {
            "instance_id": outcome.instance_id,
            "expected_feasible": instance.expected_feasible,
            "valid": outcome.policy_valid,
            "correct_classification": outcome.policy_correct_classification,
            "runtime_s": outcome.policy_runtime_s,
            "baseline": {
                "valid": outcome.baseline_valid,
                "correct_classification": outcome.baseline_correct_classification,
                "runtime_s": outcome.baseline_runtime_s,
            },
            "policy": {
                "valid": outcome.policy_valid,
                "correct_classification": outcome.policy_correct_classification,
                "runtime_s": outcome.policy_runtime_s,
                "time_reduction": outcome.policy_time_reduction,
            },
        }

    @staticmethod
    def _dataset_hash(instances: list[BenchmarkInstance]) -> str:
        payload = json.dumps([instance.to_json() for instance in instances], sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _validate(config: PairedPolicyStudyConfig) -> None:
        if config.train_instances < 1 or config.test_instances < 1:
            raise ValueError("Train and test instance counts must be positive")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--train-instances", type=int, default=40)
    parser.add_argument("--test-instances", type=int, default=120)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
    args = parser.parse_args()
    config = PairedPolicyStudyConfig(args.seed, args.train_instances, args.test_instances)
    print(PairedPolicyStudyRunner(args.output_root).run(config))


if __name__ == "__main__":
    main()
