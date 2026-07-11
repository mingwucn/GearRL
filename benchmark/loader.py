"""Load immutable certified benchmark JSON without regenerating instances."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from benchmark.generator import BenchmarkInstance
from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MaterialLoadCase, MeshEdge, Point2D


class FrozenBenchmarkLoader:
    """Rehydrate the canonical model objects stored in a frozen benchmark."""

    def load(self, root: str | Path) -> tuple[str, str, list[BenchmarkInstance]]:
        root = Path(root)
        index = json.loads((root / "index.json").read_text())
        records = []
        payloads = []
        for record in index["instances"]:
            payload = (root / "instances" / f"{record['instance_id']}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                raise ValueError(f"Frozen instance hash mismatch: {record['instance_id']}")
            payloads.append(payload)
            records.append(self._instance(json.loads(payload)))
        if len(records) != index["instance_count"]:
            raise ValueError("Frozen benchmark instance count mismatch")
        return index["dataset_id"], hashlib.sha256(b"".join(payloads)).hexdigest(), records

    @staticmethod
    def _instance(value: dict) -> BenchmarkInstance:
        problem_json = value["problem"]
        constraints = DesignConstraints(**problem_json["constraints"])
        load = problem_json.get("load_case")
        problem = DesignProblem(tuple(Point2D(**point) for point in problem_json["boundary"]), problem_json["input_stage_id"], problem_json["output_stage_id"], constraints, MaterialLoadCase(**load) if load else None, problem_json.get("units", "mm"))
        train_json = value["reference_train"]
        stages = tuple(GearStage(stage["id"], Point2D(**stage["center"]), tuple(stage["teeth"]), stage["module_mm"], tuple(stage.get("axial_layers", ()))) for stage in train_json["stages"])
        meshes = tuple(MeshEdge(**edge) for edge in train_json["meshes"])
        return BenchmarkInstance(value["instance_id"], value["seed"], problem, GearTrain(stages, meshes), value["certificate"], value["expected_feasible"], value["family"], value.get("partition", "unspecified"), value.get("difficulty", "unspecified"))
