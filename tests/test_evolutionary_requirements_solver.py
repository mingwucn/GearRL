from benchmark import SolverInputDirectoryLoader
from synthesis import EnumerativeCompoundSynthesizer, EvolutionaryCompoundSynthesizer, ProductionCandidateValidator, SolverBudget


DATASET = "data/benchmark/curated/requirements-first-50-v1/solver-inputs"


def _view(instance_id: str):
    return next(view for view in SolverInputDirectoryLoader().load(DATASET) if view.instance_id == instance_id)


def test_evolutionary_solver_is_seeded_and_certificate_admitted() -> None:
    view = _view("valid-unit-30")
    budget = SolverBudget(maximum_candidate_evaluations=1000, seed=2026, population_size=8)

    first = EvolutionaryCompoundSynthesizer(ProductionCandidateValidator(), budget).solve(view)
    second = EvolutionaryCompoundSynthesizer(ProductionCandidateValidator(), budget).solve(view)

    assert first.train == second.train
    assert first.parameter_tuples_evaluated == second.parameter_tuples_evaluated
    assert first.certificate is not None and first.certificate.valid
    assert first.search_complete is False


def test_evolutionary_solver_reports_incomplete_negative_search() -> None:
    view = _view("ratio-none-01")
    budget = SolverBudget(maximum_candidate_evaluations=300, seed=7, population_size=6)

    result = EvolutionaryCompoundSynthesizer(ProductionCandidateValidator(), budget).solve(view)

    assert result.train is None
    assert result.search_complete is False
    assert result.parameter_tuples_evaluated > 0
    assert result.parameter_tuples_evaluated <= budget.maximum_candidate_evaluations


def test_exact_solver_reports_budget_truncation_without_false_completeness() -> None:
    view = _view("ratio-none-01")
    budget = SolverBudget(maximum_candidate_evaluations=100, seed=1)

    result = EnumerativeCompoundSynthesizer(ProductionCandidateValidator(), budget=budget).solve(view)

    assert result.train is None
    assert result.parameter_tuples_evaluated == 100
    assert result.search_complete is False
