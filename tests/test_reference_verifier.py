import pytest

from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MaterialLoadCase, MeshEdge, Point2D
from physics_validator.reference_verifier import ReferenceVerifier


def _problem(target: float | None = 1.0) -> DesignProblem:
    return DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(target_speed_ratio=target, min_teeth=17, max_teeth=80),
    )


def test_verifies_compound_train_signed_speed_ratio() -> None:
    train = GearTrain(
        stages=(
            GearStage("input", Point2D(0, 0), (20,), 1.0),
            GearStage("compound", Point2D(20, 0), (20, 40), 1.0, (0, 1)),
            GearStage("output", Point2D(55, 0), (30,), 1.0, (1,)),
        ),
        meshes=(
            MeshEdge("input", 0, "compound", 0),
            MeshEdge("compound", 1, "output", 0),
        ),
    )
    certificate = ReferenceVerifier.verify(_problem(4.0 / 3.0), train)
    assert certificate.valid, [issue.message for issue in certificate.issues]
    assert certificate.signed_speed_ratio == 4.0 / 3.0


def test_rejects_endpoint_only_ratio_logic() -> None:
    train = GearTrain(
        stages=(
            GearStage("input", Point2D(0, 0), (20,), 1.0),
            GearStage("compound", Point2D(20, 0), (20, 40), 1.0, (0, 1)),
            GearStage("output", Point2D(55, 0), (30,), 1.0, (1,)),
        ),
        meshes=(MeshEdge("input", 0, "compound", 0), MeshEdge("compound", 1, "output", 0)),
    )
    certificate = ReferenceVerifier.verify(_problem(20.0 / 30.0), train)
    assert not certificate.valid
    assert any(issue.code == "speed_ratio_mismatch" for issue in certificate.issues)


def test_rejects_disconnected_or_invalid_meshes() -> None:
    train = GearTrain(
        stages=(
            GearStage("input", Point2D(0, 0), (20,), 1.0),
            GearStage("output", Point2D(45, 0), (20,), 1.0),
        ),
        meshes=(MeshEdge("input", 0, "output", 0),),
    )
    certificate = ReferenceVerifier.verify(_problem(-1.0), train)
    assert not certificate.valid
    assert any(issue.code == "mesh_center_distance" for issue in certificate.issues)


def test_detects_unintended_same_layer_compound_collision() -> None:
    train = GearTrain(
        stages=(
            GearStage("input", Point2D(0, 0), (20,), 1.0),
            GearStage("compound", Point2D(20, 0), (20, 38), 1.0, (0, 0)),
            GearStage("output", Point2D(50, 0), (30,), 1.0),
        ),
        meshes=(
            MeshEdge("input", 0, "compound", 0),
            MeshEdge("compound", 1, "output", 0),
        ),
    )
    certificate = ReferenceVerifier.verify(_problem(), train)
    assert not certificate.valid
    assert any(issue.code == "stage_collision" for issue in certificate.issues)


def test_backlash_allows_only_positive_center_distance_expansion() -> None:
    problem = DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(target_speed_ratio=-1.0, min_teeth=17, max_teeth=80, transverse_backlash_allowance_mm=0.01),
    )
    expanded = GearTrain(
        (GearStage("input", Point2D(0, 0), (20,), 1.0), GearStage("output", Point2D(20.01, 0), (20,), 1.0)),
        (MeshEdge("input", 0, "output", 0),),
    )
    compressed = GearTrain(
        (GearStage("input", Point2D(0, 0), (20,), 1.0), GearStage("output", Point2D(19.99, 0), (20,), 1.0)),
        (MeshEdge("input", 0, "output", 0),),
    )
    assert ReferenceVerifier.verify(problem, expanded).valid
    assert not ReferenceVerifier.verify(problem, compressed).valid


def test_rejects_equal_center_distance_with_incompatible_modules() -> None:
    train = GearTrain(
        (
            GearStage("input", Point2D(0, 0), (20,), 1.0),
            GearStage("output", Point2D(30, 0), (20,), 2.0),
        ),
        (MeshEdge("input", 0, "output", 0),),
    )

    certificate = ReferenceVerifier.verify(_problem(-1.0), train)

    assert not certificate.valid
    assert any(issue.code == "mesh_module_mismatch" for issue in certificate.issues)


def test_rejects_standard_unshifted_gear_with_undercut_risk() -> None:
    problem = DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(target_speed_ratio=-1.0, min_teeth=10, max_teeth=80),
    )
    train = GearTrain(
        (GearStage("input", Point2D(0, 0), (16,), 1.0), GearStage("output", Point2D(16, 0), (16,), 1.0)),
        (MeshEdge("input", 0, "output", 0),),
    )

    certificate = ReferenceVerifier.verify(problem, train)

    assert not certificate.valid
    assert any(issue.code == "standard_undercut_risk" for issue in certificate.issues)


@pytest.mark.parametrize(
    "factory",
    (
        lambda: Point2D(float("nan"), 0.0),
        lambda: GearStage("input", Point2D(0.0, 0.0), (20,), float("nan")),
        lambda: DesignConstraints(float("inf")),
        lambda: MaterialLoadCase("steel", 1.0, 10.0, 210000.0, 0.3, float("nan")),
        lambda: MeshEdge("input", 0, "output", 0, float("nan")),
    ),
)
def test_canonical_objects_reject_non_finite_values(factory) -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        factory()


def test_certificate_records_semantic_model_v3() -> None:
    train = GearTrain(
        (GearStage("input", Point2D(0, 0), (20,), 1.0), GearStage("output", Point2D(20, 0), (20,), 1.0)),
        (MeshEdge("input", 0, "output", 0),),
    )

    assert ReferenceVerifier.verify(_problem(-1.0), train).model_version == "certified-planar-v3"
