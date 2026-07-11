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
    assert not certificate.valid
    assert len(certificate.cae_reports) == 2
    assert any(issue.code == "cae_not_admission_qualified" for issue in certificate.issues)
    assert certificate.model_identity.planar_model == "certified-planar-v3"
    assert certificate.model_identity.static_strength_model == "involute-tooth-root-plane-stress-v3"
    assert certificate.model_identity.strength_qualification_evidence == "cae-refinement-audit-v1"
    with pytest.raises(TypeError):
        certificate.cae_reports[0]["model_version"] = "mutated"


def test_cae_certificate_rejects_excessive_safety_requirement() -> None:
    certificate = ReferenceVerifier.verify_with_cae(_problem(1e9), _train())
    assert not certificate.valid
    assert any(issue.code == "cae_safety_factor" for issue in certificate.issues)


def test_per_mesh_efficiency_preserves_action_reaction_contact_force() -> None:
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
    by_member = {}
    for report in certificate.cae_reports:
        by_member[(report["stage_id"], report["member"])] = report

    assert not certificate.valid
    assert any(issue.code == "cae_not_admission_qualified" for issue in certificate.issues)
    assert by_member[("input", 0)]["cumulative_mesh_efficiency"] == 1.0
    assert by_member[("compound", 0)]["cumulative_mesh_efficiency"] == 1.0
    assert by_member[("compound", 1)]["cumulative_mesh_efficiency"] == 0.8
    assert by_member[("output", 0)]["cumulative_mesh_efficiency"] == 0.8
    assert by_member[("input", 0)]["tangential_force_n"] == pytest.approx(by_member[("compound", 0)]["tangential_force_n"])
    assert by_member[("compound", 1)]["tangential_force_n"] == pytest.approx(by_member[("output", 0)]["tangential_force_n"])
    assert by_member[("input", 0)]["transmitted_torque_nm"] == 10.0
    assert by_member[("compound", 0)]["transmitted_torque_nm"] == 10.0
    assert by_member[("compound", 1)]["transmitted_torque_nm"] == 8.0
    assert by_member[("output", 0)]["transmitted_torque_nm"] == 8.0
