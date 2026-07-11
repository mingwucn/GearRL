"""Contract tests for the paired learned-policy effect gate."""

import numpy as np
import torch

from benchmark.generator import BenchmarkGenerator
from evaluation.paired_efficiency import PairedEfficiencyStudy
from synthesis.baselines import BranchAndBoundSolver
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import BranchOrderingImitationTrainer, CertifiedDemonstrationCollector, DemonstrationBatch, LearnedBranchOrderingPolicy


def test_paired_study_preserves_certificate_backed_outcomes_and_reports_gate() -> None:
    torch.manual_seed(17)
    instances = BenchmarkGenerator().generate_compound_instances(17, 4)
    policy = LearnedBranchOrderingPolicy(max_actions=3)
    collector = CertifiedDemonstrationCollector()
    batches = [collector.collect(CertifiedSynthesisGraph(item.problem, item.reference_train.stages, item.reference_train.meshes), 3) for item in instances]
    batch = DemonstrationBatch(np.concatenate([item.features for item in batches]), np.concatenate([item.action_indices for item in batches]))
    BranchOrderingImitationTrainer(policy).train(batch, epochs=100)

    study = PairedEfficiencyStudy(BranchAndBoundSolver(), max_actions=3, timing_repetitions=1, bootstrap_samples=100, bootstrap_seed=9)
    outcomes = study.evaluate(policy, instances)
    summary = study.summarize(outcomes)

    assert len(outcomes) == 4
    assert all(outcome.baseline_valid and outcome.policy_valid for outcome in outcomes)
    assert all(outcome.baseline_correct_classification and outcome.policy_correct_classification for outcome in outcomes)
    assert summary.observations == 4
    assert summary.policy_valid_rate == 1.0
    assert summary.bootstrap_low <= summary.bootstrap_high
