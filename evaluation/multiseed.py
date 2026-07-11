"""Repeatable multi-seed study for certified learned branch ordering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from benchmark.generator import BenchmarkGenerator
from evaluation.policy import LearnedPolicyEvaluator, PolicyOutcome
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import BranchOrderingImitationTrainer, CertifiedDemonstrationCollector, DemonstrationBatch, LearnedBranchOrderingPolicy, PPOBranchRefinementTrainer


@dataclass(frozen=True)
class SeedStudyOutcome:
    seed: int
    valid_rate: float
    median_runtime_s: float
    outcomes: tuple[PolicyOutcome, ...]


class MultiSeedPolicyStudy:
    """Run identical train/evaluation protocol across independent random seeds."""

    def __init__(self, max_actions: int = 3, train_instances: int = 8, test_instances: int = 20):
        self._max_actions = max_actions
        self._train_instances = train_instances
        self._test_instances = test_instances

    def run(self, seeds: tuple[int, ...]) -> list[SeedStudyOutcome]:
        if not seeds:
            raise ValueError("At least one seed is required")
        results = []
        generator = BenchmarkGenerator()
        for seed in seeds:
            torch.manual_seed(seed)
            policy = LearnedBranchOrderingPolicy(self._max_actions)
            train = generator.generate_compound_instances(seed, self._train_instances)
            batch = self._demonstrations(train)
            BranchOrderingImitationTrainer(policy).train(batch, epochs=10)
            for instance in train:
                graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
                from synthesis.certified_environment import CertifiedBranchOrderingEnvironment
                PPOBranchRefinementTrainer(policy).refine_episode(CertifiedBranchOrderingEnvironment(graph, self._max_actions))
            outcomes = tuple(LearnedPolicyEvaluator(self._max_actions).evaluate(policy, generator.generate_compound_instances(seed + 10_000, self._test_instances)))
            results.append(SeedStudyOutcome(seed, sum(item.valid for item in outcomes) / len(outcomes), float(np.median([item.runtime_s for item in outcomes])), outcomes))
        return results

    def _demonstrations(self, instances) -> DemonstrationBatch:
        collector = CertifiedDemonstrationCollector()
        batches = [collector.collect(CertifiedSynthesisGraph(item.problem, item.reference_train.stages, item.reference_train.meshes), self._max_actions) for item in instances]
        return DemonstrationBatch(np.concatenate([batch.features for batch in batches]), np.concatenate([batch.action_indices for batch in batches]))
