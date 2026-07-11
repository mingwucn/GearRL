from benchmark.generator import BenchmarkGenerator
from evaluation.comparison import CertifiedSolverComparison
from evaluation.robustness import GeometricToleranceEvaluator
from synthesis.baselines import BranchAndBoundSolver, RouteFirstSolver


def test_solver_comparison_records_only_certificate_backed_outcomes() -> None:
    instances = BenchmarkGenerator().generate_suite(5, 2, 1)
    outcomes = CertifiedSolverComparison().evaluate(instances, {"branch": BranchAndBoundSolver(), "route": RouteFirstSolver()})
    assert len(outcomes) == 6
    assert all(outcome.correct_classification for outcome in outcomes)


def test_tolerance_evaluator_rechecks_every_perturbed_layout() -> None:
    instance = BenchmarkGenerator().generate_compound_instances(5, 1)[0]
    outcomes = GeometricToleranceEvaluator().evaluate(instance.problem, instance.reference_train, (0.0, 0.01))
    assert outcomes[0].valid is True
    assert outcomes[1].valid is False
