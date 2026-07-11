from benchmark import SolverInputDirectoryLoader
from synthesis import CpSatCompoundSynthesizer, ProductionCandidateValidator, SolverBudget


DATASET = "data/benchmark/curated/requirements-first-50-v1/solver-inputs"


def _view(instance_id: str):
    return next(view for view in SolverInputDirectoryLoader().load(DATASET) if view.instance_id == instance_id)


def test_cp_sat_synthesizes_exact_ratio_with_certificate() -> None:
    result = CpSatCompoundSynthesizer(
        ProductionCandidateValidator(),
        SolverBudget(7000, 2026, maximum_time_s=5.0),
    ).solve(_view("valid-high-35"))

    assert result.train is not None
    assert result.certificate is not None and result.certificate.valid
    assert result.parameter_tuples_evaluated >= 1
    assert result.search_complete is False


def test_cp_sat_proves_ratio_infeasibility_without_candidate_enumeration() -> None:
    result = CpSatCompoundSynthesizer(
        ProductionCandidateValidator(),
        SolverBudget(7000, 2026, maximum_time_s=5.0),
    ).solve(_view("ratio-none-01"))

    assert result.train is None
    assert result.search_complete is True
    assert result.parameter_tuples_evaluated == 0


def test_cp_sat_proves_shaft_spacing_infeasibility() -> None:
    result = CpSatCompoundSynthesizer(
        ProductionCandidateValidator(),
        SolverBudget(7000, 2026, maximum_time_s=5.0),
    ).solve(_view("spacing-none-01"))

    assert result.train is None
    assert result.search_complete is True
