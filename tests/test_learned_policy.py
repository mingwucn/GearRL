import torch

from benchmark.generator import BenchmarkGenerator
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import BranchOrderingImitationTrainer, CertifiedDemonstrationCollector, LearnedBranchOrderingPolicy


def test_learned_policy_selects_only_certified_actions_after_imitation_training() -> None:
    torch.manual_seed(7)
    instance = BenchmarkGenerator().generate_compound_instances(7, 1)[0]
    graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
    policy = LearnedBranchOrderingPolicy(max_actions=3)
    batch = CertifiedDemonstrationCollector().collect(graph, max_actions=3)
    assert len(batch.features) == 2
    assert BranchOrderingImitationTrainer(policy).train(batch, epochs=4) >= 0
    edge = policy.select(graph, "input", {"input"})
    assert edge in graph.candidates("input", {"input"})
