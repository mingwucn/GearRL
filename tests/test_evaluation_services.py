from benchmark.generator import BenchmarkGenerator
from evaluation.comparison import CertifiedSolverComparison
from evaluation.robustness import GeometricToleranceEvaluator
from synthesis.baselines import BranchAndBoundSolver, RouteFirstSolver
from synthesis.certified_graph import SynthesisResult


class ForgedCertificateSolver(BranchAndBoundSolver):
    """Return an invalid train while claiming a valid serialized certificate."""

    def solve(self, graph):
        train = graph.solve().train
        changed = __import__("dataclasses").replace(
            train,
            stages=(*train.stages[:-1], __import__("dataclasses").replace(train.stages[-1], teeth=(1,))),
        )
        return SynthesisResult(changed, (0, 0.0), {"valid": True})


def test_solver_comparison_records_only_certificate_backed_outcomes() -> None:
    instances = BenchmarkGenerator().generate_suite(5, 2, 1)
    outcomes = CertifiedSolverComparison().evaluate(instances, {"branch": BranchAndBoundSolver(), "route": RouteFirstSolver()})
    assert len(outcomes) == 6
    assert all(outcome.correct_classification for outcome in outcomes if outcome.solver_name == "branch")
    assert any(not outcome.correct_classification for outcome in outcomes if outcome.solver_name == "route")


def test_tolerance_evaluator_rechecks_every_perturbed_layout() -> None:
    instance = BenchmarkGenerator().generate_compound_instances(5, 1)[0]
    outcomes = GeometricToleranceEvaluator().evaluate(instance.problem, instance.reference_train, (0.0, 0.01))
    assert outcomes[0].valid is True
    assert outcomes[1].valid is False


def test_solver_comparison_rejects_forged_certificate_boolean() -> None:
    instance = BenchmarkGenerator().generate_compound_instances(11, 1)[0]
    outcome = CertifiedSolverComparison().evaluate([instance], {"forged": ForgedCertificateSolver()})[0]
    assert outcome.valid is False
