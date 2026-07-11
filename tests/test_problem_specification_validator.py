from dataclasses import replace

from benchmark import CuratedBenchmarkLoader, SolverInputDirectoryLoader
from common.design_models import GearStage, GearTrain, MeshEdge, Point2D
from synthesis import ProductionCandidateValidator


DATASET = "data/benchmark/curated/requirements-first-50-v2"


def _valid_case():
    dataset = CuratedBenchmarkLoader().load(DATASET)
    evidence = next(payload for payload in dataset.evidence_payloads if payload["expected_feasible"])
    view = next(view for view in SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs") if view.instance_id == evidence["instance_id"])
    payload = evidence["reference_train"]
    stages = tuple(
        GearStage(stage["id"], Point2D(**stage["center"]), tuple(stage["teeth"]), stage["module_mm"], tuple(stage.get("axial_layers", ())))
        for stage in payload["stages"]
    )
    train = GearTrain(stages, tuple(MeshEdge(**edge) for edge in payload["meshes"]))
    return view.specification, train


def _replace_stage(train: GearTrain, stage_id: str, **changes) -> GearTrain:
    stages = tuple(replace(stage, **changes) if stage.id == stage_id else stage for stage in train.stages)
    return GearTrain(stages, train.meshes)


def _issue_codes(specification, train: GearTrain) -> set[str]:
    return {issue.code for issue in ProductionCandidateValidator().validate(specification, train).issues}


def test_reference_witness_satisfies_complete_problem_specification() -> None:
    specification, train = _valid_case()
    certificate = ProductionCandidateValidator().validate(specification, train)
    assert certificate.valid
    assert certificate.model_identity.specification_model == "requirements-first-v1"


def test_prescribed_shaft_position_is_independently_enforced() -> None:
    specification, reference = _valid_case()
    train = _replace_stage(reference, "input", center=Point2D(0.01, 0.0))
    assert "prescribed_shaft_position" in _issue_codes(specification, train)


def test_allowed_module_is_independently_enforced() -> None:
    specification, reference = _valid_case()
    train = GearTrain(tuple(replace(stage, module_mm=stage.module_mm + 0.1) for stage in reference.stages), reference.meshes)
    assert "design_space_module" in _issue_codes(specification, train)


def test_stage_count_bounds_are_independently_enforced() -> None:
    specification, reference = _valid_case()
    extra = GearStage("unconnected", Point2D(80.0, 80.0), (20,), reference.stages[0].module_mm, (0,))
    train = GearTrain((*reference.stages, extra), reference.meshes)
    assert "design_space_stage_count" in _issue_codes(specification, train)


def test_compound_member_limit_is_independently_enforced() -> None:
    specification, reference = _valid_case()
    compound = next(stage for stage in reference.stages if stage.id == "compound")
    train = _replace_stage(reference, "compound", teeth=(*compound.teeth, compound.teeth[-1]), axial_layers=(0, 1, 1))
    assert "design_space_compound_members" in _issue_codes(specification, train)


def test_axial_layer_limit_is_independently_enforced() -> None:
    specification, reference = _valid_case()
    train = _replace_stage(reference, "output", axial_layers=(specification.design_space.axial_layer_count,))
    assert "design_space_axial_layer" in _issue_codes(specification, train)


def test_mesh_tolerance_is_fixed_by_design_space() -> None:
    specification, reference = _valid_case()
    changed = replace(reference.meshes[0], center_distance_tolerance_mm=1e-6)
    train = GearTrain(reference.stages, (changed, *reference.meshes[1:]))
    assert "design_space_mesh_tolerance" in _issue_codes(specification, train)


def test_topology_family_rejects_alternate_mesh_graph() -> None:
    specification, reference = _valid_case()
    changed = replace(reference.meshes[1], driver_member=0)
    train = GearTrain(reference.stages, (reference.meshes[0], changed))
    assert "topology_family_meshes" in _issue_codes(specification, train)


def test_topology_family_rejects_noncanonical_layers() -> None:
    specification, reference = _valid_case()
    train = _replace_stage(reference, "compound", axial_layers=(1, 0))
    assert "topology_family_layers" in _issue_codes(specification, train)
