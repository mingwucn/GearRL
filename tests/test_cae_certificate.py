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
