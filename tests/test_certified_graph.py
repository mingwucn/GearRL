from common.design_models import DesignConstraints, DesignProblem, GearStage, MeshEdge, Point2D
from synthesis.certified_graph import CertifiedSynthesisGraph


def test_certified_graph_selects_valid_compound_path() -> None:
    problem = DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(target_speed_ratio=4.0 / 3.0, min_teeth=17, max_teeth=80),
    )
    stages = (
        GearStage("input", Point2D(0, 0), (20,), 1.0),
        GearStage("compound", Point2D(20, 0), (20, 40), 1.0, (0, 1)),
        GearStage("output", Point2D(55, 0), (30,), 1.0, (1,)),
        GearStage("wrong", Point2D(25, 25), (20,), 1.0),
    )
    graph = CertifiedSynthesisGraph(
        problem,
        stages,
        (
            MeshEdge("input", 0, "compound", 0),
            MeshEdge("compound", 1, "output", 0),
            MeshEdge("input", 0, "wrong", 0),
        ),
    )
    result = graph.solve()
    assert result is not None
    assert [stage.id for stage in result.train.stages] == ["input", "compound", "output"]
    assert result.certificate_json["valid"] is True


def test_certified_graph_returns_none_when_no_path_is_valid() -> None:
    problem = DesignProblem(
        boundary=(Point2D(-100, -100), Point2D(100, -100), Point2D(100, 100), Point2D(-100, 100)),
        input_stage_id="input",
        output_stage_id="output",
        constraints=DesignConstraints(target_speed_ratio=1.0, min_teeth=17, max_teeth=80),
    )
    graph = CertifiedSynthesisGraph(
        problem,
        (GearStage("input", Point2D(0, 0), (20,), 1.0), GearStage("output", Point2D(20, 0), (20,), 1.0)),
        (MeshEdge("input", 0, "output", 0),),
    )
    assert graph.solve() is None
