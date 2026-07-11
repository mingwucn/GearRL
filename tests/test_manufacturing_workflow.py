import json

import pytest

from benchmark.generator import BenchmarkGenerator
from common.design_models import DesignConstraints, DesignProblem
from manufacturing.workflow import ManufacturingWorkflow


def test_workflow_exports_manifest_bound_to_independent_certificate(tmp_path) -> None:
    instance = BenchmarkGenerator().generate_compound_instances(33, 1)[0]
    artifact = ManufacturingWorkflow().export(instance.problem, instance.reference_train, tmp_path)
    assert artifact.certificate["valid"] is True
    assert (tmp_path / f"{artifact.artifact_id}.json").is_file()
    assert json.loads((tmp_path / f"{artifact.artifact_id}.json").read_text())["dxf_path"] == artifact.dxf_path


def test_workflow_rejects_invalid_layouts(tmp_path) -> None:
    instance = BenchmarkGenerator().generate_compound_instances(33, 1)[0]
    invalid_problem = DesignProblem(
        instance.problem.boundary,
        instance.problem.input_stage_id,
        instance.problem.output_stage_id,
        DesignConstraints(target_speed_ratio=99.0, min_teeth=18, max_teeth=48),
    )
    with pytest.raises(ValueError):
        ManufacturingWorkflow().export(invalid_problem, instance.reference_train, tmp_path)
