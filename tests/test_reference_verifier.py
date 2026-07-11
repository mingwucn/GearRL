from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MeshEdge, Point2D
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
