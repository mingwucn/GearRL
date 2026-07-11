import pytest

from common.design_models import (
    DesignConstraints,
    DesignProblem,
    GearStage,
    GearTrain,
    MaterialLoadCase,
    MeshEdge,
    Point2D,
)
from physics_validator.reference_verifier import ReferenceVerifier


def _problem(minimum_safety_factor: float) -> DesignProblem:
    return DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(
            target_speed_ratio=-1.0,
            min_teeth=17,
            max_teeth=80,
            min_safety_factor=minimum_safety_factor,
        ),
        load_case=MaterialLoadCase("steel", 5.0, 10.0, 210_000.0, 0.3, 300.0),
    )


def _train() -> GearTrain:
    return GearTrain(
        (GearStage("input", Point2D(0, 0), (24,), 2.0), GearStage("output", Point2D(48, 0), (24,), 2.0)),
        (MeshEdge("input", 0, "output", 0),),
    )


def test_cae_certificate_includes_member_reports() -> None:
    certificate = ReferenceVerifier.verify_with_cae(_problem(0.01), _train())
    assert certificate.valid
    assert len(certificate.cae_reports) == 2


def test_cae_certificate_rejects_excessive_safety_requirement() -> None:
    certificate = ReferenceVerifier.verify_with_cae(_problem(1e9), _train())
    assert not certificate.valid
    assert any(issue.code == "cae_safety_factor" for issue in certificate.issues)


def test_per_mesh_efficiency_propagates_power_and_stage_torque() -> None:
    problem = DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(1.0, min_teeth=18, max_teeth=80, min_safety_factor=0.01),
        load_case=MaterialLoadCase("steel", 10.0, 10.0, 210_000.0, 0.3, 800.0, efficiency=0.8),
    )
    train = GearTrain(
        (
            GearStage("input", Point2D(0, 0), (20,), 1.0, (0,)),
            GearStage("compound", Point2D(20, 0), (20, 20), 1.0, (0, 1)),
            GearStage("output", Point2D(40, 0), (20,), 1.0, (1,)),
        ),
        (MeshEdge("input", 0, "compound", 0), MeshEdge("compound", 1, "output", 0)),
    )

    certificate = ReferenceVerifier.verify_with_cae(problem, train)
    by_stage = {}
    for report in certificate.cae_reports:
        by_stage.setdefault(report["stage_id"], report)

    assert certificate.valid
    assert by_stage["input"]["cumulative_mesh_efficiency"] == 1.0
    assert by_stage["compound"]["cumulative_mesh_efficiency"] == 0.8
    assert by_stage["output"]["cumulative_mesh_efficiency"] == pytest.approx(0.64)
    assert by_stage["input"]["transmitted_torque_nm"] == 10.0
    assert by_stage["compound"]["transmitted_torque_nm"] == 8.0
    assert by_stage["output"]["transmitted_torque_nm"] == pytest.approx(6.4)
