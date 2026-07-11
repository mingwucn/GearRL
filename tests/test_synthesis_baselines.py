from benchmark.generator import BenchmarkGenerator
from synthesis.baselines import BranchAndBoundSolver, RandomizedSearchSolver, RouteFirstSolver
from synthesis.certified_graph import CertifiedSynthesisGraph


def test_certified_baselines_return_only_independently_valid_results() -> None:
    instance = BenchmarkGenerator().generate_compound_instances(17, 1)[0]
    graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
    for solver in (BranchAndBoundSolver(), RouteFirstSolver(), RandomizedSearchSolver(seed=17)):
        result = solver.solve(graph)
        assert result is not None
        assert result.certificate_json["valid"] is True
