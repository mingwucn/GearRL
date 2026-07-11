import torch

from benchmark.generator import BenchmarkGenerator
from synthesis.certified_environment import CertifiedBranchOrderingEnvironment
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import LearnedBranchOrderingPolicy, PPOBranchRefinementTrainer


def test_ppo_refinement_environment_terminates_with_independent_certificate() -> None:
    torch.manual_seed(11)
    instance = BenchmarkGenerator().generate_compound_instances(11, 1)[0]
    graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
    environment = CertifiedBranchOrderingEnvironment(graph, max_actions=3)
    policy = LearnedBranchOrderingPolicy(max_actions=3)
    assert isinstance(PPOBranchRefinementTrainer(policy).refine_episode(environment), float)
