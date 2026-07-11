from dataclasses import replace

import pytest

from benchmark import (
    BenchmarkGenerator,
    DesignSpace,
    GroundTruthEvidence,
    PrescribedShaft,
    ProblemSpecification,
    RequirementsFirstBenchmarkCase,
    SolverBenchmarkView,
    SolverPayloadGuard,
)


class RequirementsFirstFixtureFactory:
    def build(self) -> RequirementsFirstBenchmarkCase:
        legacy = BenchmarkGenerator().generate_compound_instances(19, 1)[0]
        stages = legacy.reference_train.stage_map()
        specification = ProblemSpecification(
            schema_version="requirements-first-v1",
            problem=legacy.problem,
            design_space=DesignSpace((1.0, 1.25, 1.5, 2.0), 3, 6),
            prescribed_shafts=(
                PrescribedShaft("input", stages["input"].center),
                PrescribedShaft("output", stages["output"].center),
            ),
        )
        return RequirementsFirstBenchmarkCase(
            SolverBenchmarkView(legacy.instance_id, "requirements-first-contract", "test", specification),
            GroundTruthEvidence(
                expected_feasible=True,
                proof_kind="constructive-witness",
                oracle_version="fixture-v1",
                reference_train=legacy.reference_train,
                certificate=legacy.certificate,
            ),
        )


def test_solver_payload_excludes_all_ground_truth_fields() -> None:
    case = RequirementsFirstFixtureFactory().build()
    payload = case.solver_payload()

    SolverPayloadGuard().validate(payload)
    serialized = repr(payload)
    for forbidden in ("reference_train", "certificate", "expected_feasible", "proof_kind", "oracle_version"):
        assert forbidden not in serialized


def test_guard_rejects_nested_evaluator_evidence() -> None:
    case = RequirementsFirstFixtureFactory().build()
    poisoned = {**case.solver_payload(), "metadata": {"expected_feasible": True}}

    with pytest.raises(ValueError, match="expected_feasible"):
        SolverPayloadGuard().validate(poisoned)


def test_negative_ground_truth_requires_a_global_proof_kind() -> None:
    evidence = GroundTruthEvidence(False, "unknown", "oracle-under-development")
    assert evidence.globally_proven is False

    with pytest.raises(ValueError, match="negative label"):
        GroundTruthEvidence(False, "constructive-witness", "invalid")


def test_problem_specification_requires_exactly_two_finite_prescribed_shafts() -> None:
    case = RequirementsFirstFixtureFactory().build()
    specification = case.solver_view.specification

    with pytest.raises(ValueError, match="Exactly one input and one output"):
        replace(specification, prescribed_shafts=specification.prescribed_shafts[:1])


def test_legacy_family_is_explicitly_not_an_inverse_synthesis_dataset() -> None:
    assert "path-selection" in BenchmarkGenerator.__doc__
