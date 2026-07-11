import pytest

from benchmark.generator import BenchmarkGenerator
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.policy_interface import CertifiedActionSpace


def test_action_mask_only_exposes_unvisited_certified_transitions() -> None:
    instance = BenchmarkGenerator().generate_compound_instances(9, 1)[0]
    graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
    actions = CertifiedActionSpace(graph, max_actions=3)
    assert actions.action_mask("input", {"input"}).tolist() == [True, False, False]
    edge = actions.select("input", {"input"}, 0)
    assert edge.driven_stage_id == "compound"
    with pytest.raises(ValueError):
        actions.select("input", {"input", "compound"}, 0)
