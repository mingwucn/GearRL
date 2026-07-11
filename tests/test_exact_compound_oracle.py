import inspect
from dataclasses import replace

from benchmark import (
    DesignSpace,
    ExactCompoundTrainOracle,
    PrescribedShaft,
    ProblemSpecification,
    ReplayableExactCompoundTrainOracle,
    ReplayableOracleProofVerifier,
    SolverBenchmarkView,
)
from common.design_models import DesignConstraints, DesignProblem, Point2D
from synthesis.requirements_solver import (
    CpSatCompoundSynthesizer,
    EnumerativeCompoundSynthesizer,
    EvolutionaryCompoundSynthesizer,
    ProductionCandidateValidator,
    SolverBudget,
)


class OracleFixtureFactory:
    def build(
        self,
        terminal_distance: float,
        target_ratio: float,
        minimum_teeth: int = 20,
        maximum_teeth: int = 20,
        input_stage_id: str = "input",
        output_stage_id: str = "output",
    ) -> SolverBenchmarkView:
        boundary = (Point2D(-60, -60), Point2D(60, -60), Point2D(60, 60), Point2D(-60, 60))
        problem = DesignProblem(
            boundary=boundary,
            input_stage_id=input_stage_id,
            output_stage_id=output_stage_id,
            constraints=DesignConstraints(target_ratio, min_teeth=minimum_teeth, max_teeth=maximum_teeth),
        )
        specification = ProblemSpecification(
            "requirements-first-v1",
            problem,
            DesignSpace((1.0,), 3, 3),
            (PrescribedShaft("input", Point2D(0, 0)), PrescribedShaft("output", Point2D(terminal_distance, 0))),
        )
        return SolverBenchmarkView("oracle-fixture", "curated-compound", "test", specification)


def test_exact_oracle_constructs_non_collinear_witness_from_requirements() -> None:
    view = OracleFixtureFactory().build(30.0, 1.0)

    result = ExactCompoundTrainOracle().solve(view)

    assert result.proof.feasible
    assert result.witness is not None
    assert abs(result.witness.stage_map()["compound"].center.y) > 1.0
    assert result.to_evidence().globally_proven


def test_oracle_and_solvers_honor_noncanonical_terminal_stage_ids() -> None:
    view = OracleFixtureFactory().build(30.0, 1.0, input_stage_id="motor-shaft", output_stage_id="load-shaft")
    validator = ProductionCandidateValidator()
    budget = SolverBudget(maximum_candidate_evaluations=100, seed=2026, population_size=4, maximum_time_s=5.0)
    oracle_result = ExactCompoundTrainOracle().solve(view)
    solver_results = (
        EnumerativeCompoundSynthesizer(validator, budget=budget).solve(view),
        EvolutionaryCompoundSynthesizer(validator, budget).solve(view),
        CpSatCompoundSynthesizer(validator, budget).solve(view),
    )

    trains = (oracle_result.witness, *(result.train for result in solver_results))
    assert all(train is not None for train in trains)
    for train in trains:
        assert train is not None
        assert {"motor-shaft", "load-shaft"}.issubset(train.stage_map())
        assert validator.validate(view.specification, train).valid


def test_exact_oracle_proves_bounded_ratio_infeasibility() -> None:
    view = OracleFixtureFactory().build(30.0, 1.1)

    result = ExactCompoundTrainOracle().solve(view)

    assert not result.proof.feasible
    assert result.proof.design_space_complete
    assert result.proof.evaluated_parameter_tuples == 1
    assert result.witness is None
    assert result.to_evidence().globally_proven


def test_exact_oracle_proves_geometric_infeasibility() -> None:
    view = OracleFixtureFactory().build(50.0, 1.0)

    result = ExactCompoundTrainOracle().solve(view)

    assert not result.proof.feasible
    assert result.proof.evaluated_parameter_tuples == 1
    assert result.proof.evaluated_placements == 0


def test_oracle_has_no_dependency_on_production_reference_verifier() -> None:
    source = inspect.getsource(inspect.getmodule(ExactCompoundTrainOracle))
    assert "ReferenceVerifier" not in source


def test_exact_oracle_eliminates_undercut_prone_space() -> None:
    view = OracleFixtureFactory().build(24.0, 1.0, 16, 16)

    result = ExactCompoundTrainOracle().solve(view)

    assert not result.proof.feasible
    assert result.proof.design_space_complete
    assert result.proof.evaluated_parameter_tuples == 1


def test_replayable_negative_proof_binds_every_tuple_disposition() -> None:
    view = OracleFixtureFactory().build(30.0, 1.1, 20, 21)
    proof = ReplayableExactCompoundTrainOracle().solve(view).proof

    assert proof.elimination_ledger is not None
    assert proof.elimination_ledger["tuple_count"] == 16
    assert sum(proof.elimination_ledger["disposition_counts"].values()) == 16
    assert ReplayableOracleProofVerifier().verify(view, proof) == proof
    corrupted = replace(
        proof,
        elimination_ledger={**proof.elimination_ledger, "ledger_sha256": "0" * 64},
    )
    with __import__("pytest").raises(ValueError, match="proof mismatch"):
        ReplayableOracleProofVerifier().verify(view, corrupted)


def test_exact_oracle_refuses_completeness_for_broader_stage_or_backlash_domains() -> None:
    view = OracleFixtureFactory().build(30.0, 1.1)
    broad_space = replace(view.specification.design_space, minimum_stage_count=2, maximum_stage_count=4)
    broad = replace(view, specification=replace(view.specification, design_space=broad_space))
    allowance_constraints = replace(view.specification.problem.constraints, transverse_backlash_allowance_mm=0.01)
    allowance = replace(
        view,
        specification=replace(view.specification, problem=replace(view.specification.problem, constraints=allowance_constraints)),
    )
    tolerant_space = replace(view.specification.design_space, mesh_center_distance_tolerance_mm=1e-6)
    tolerant = replace(view, specification=replace(view.specification, design_space=tolerant_space))

    assert not ExactCompoundTrainOracle().solve(broad).proof.design_space_complete
    assert not ExactCompoundTrainOracle().solve(allowance).proof.design_space_complete
    assert not ExactCompoundTrainOracle().solve(tolerant).proof.design_space_complete
