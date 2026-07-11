import torch

from benchmark.generator import BenchmarkGenerator
from evaluation.policy import LearnedPolicyEvaluator
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import BranchOrderingImitationTrainer, CertifiedDemonstrationCollector, LearnedBranchOrderingPolicy


def test_policy_evaluator_reports_only_certificate_backed_results() -> None:
    torch.manual_seed(31)
    instances = BenchmarkGenerator().generate_compound_instances(31, 4)
    policy = LearnedBranchOrderingPolicy(max_actions=3)
    collector = CertifiedDemonstrationCollector()
    batches = [collector.collect(CertifiedSynthesisGraph(item.problem, item.reference_train.stages, item.reference_train.meshes), 3) for item in instances]
    import numpy as np
    batch = type(batches[0])(np.concatenate([item.features for item in batches]), np.concatenate([item.action_indices for item in batches]))
    BranchOrderingImitationTrainer(policy).train(batch, epochs=100)
    outcomes = LearnedPolicyEvaluator(3).evaluate(policy, instances)
    assert all(outcome.valid and outcome.certificate_json for outcome in outcomes)
