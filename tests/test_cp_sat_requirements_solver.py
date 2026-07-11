from dataclasses import replace

from benchmark import SolverInputDirectoryLoader
from synthesis import CpSatCompoundSynthesizer, EnumerativeCompoundSynthesizer, ProductionCandidateValidator, SolverBudget


DATASET = "data/benchmark/curated/requirements-first-50-v2/solver-inputs"


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


def test_cp_sat_matches_enumerator_for_non_exact_tolerance_witness() -> None:
    original = _view("valid-high-35")
    target = original.specification.problem.constraints.target_speed_ratio
    assert target is not None
    constraints = replace(
        original.specification.problem.constraints,
        target_speed_ratio=target + 5e-5,
        ratio_tolerance=1e-4,
    )
    problem = replace(original.specification.problem, constraints=constraints)
    specification = replace(original.specification, problem=problem)
    view = replace(original, specification=specification)
    budget = SolverBudget(7000, 2026, maximum_time_s=5.0)

    cp_sat = CpSatCompoundSynthesizer(ProductionCandidateValidator(), budget).solve(view)
    enumeration = EnumerativeCompoundSynthesizer(ProductionCandidateValidator(), budget=budget).solve(view)

    assert enumeration.train is not None
    assert cp_sat.train is not None
    assert cp_sat.certificate is not None and cp_sat.certificate.valid


def test_cp_sat_proves_negative_ratio_infeasible_for_fixed_even_mesh_topology() -> None:
    original = _view("valid-high-35")
    constraints = replace(original.specification.problem.constraints, target_speed_ratio=-1.0)
    view = replace(
        original,
        specification=replace(original.specification, problem=replace(original.specification.problem, constraints=constraints)),
    )
    result = CpSatCompoundSynthesizer(ProductionCandidateValidator(), SolverBudget(7000, 2026)).solve(view)
    assert result.train is None
    assert result.search_complete
    assert result.parameter_tuples_evaluated == 0
