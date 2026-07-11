"""Explicit analytical corpus for the certified planar verifier boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import ceil, hypot, isclose, radians, sin
from pathlib import Path

from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MeshEdge, Point2D
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class ValidatorCase:
    """One authored expected outcome with a concrete canonical design."""

    case_id: str
    family: str
    problem: DesignProblem
    train: GearTrain
    expected_valid: bool
    expected_issue_codes: tuple[str, ...] = ()


class ValidatorCaseBuilder:
    """Construct cohesive simple and compound canonical case objects."""

    BOUNDARY = (Point2D(-120, -120), Point2D(120, -120), Point2D(120, 120), Point2D(-120, 120))

    def simple(
        self,
        case_id: str,
        family: str,
        driver_teeth: int,
        driven_teeth: int,
        *,
        target: float | None = None,
        center_offset_mm: float = 0.0,
        module_driver: float = 1.0,
        module_driven: float | None = None,
        driver_layer: int = 0,
        driven_layer: int = 0,
        boundary: tuple[Point2D, ...] | None = None,
        min_teeth: int = 18,
        max_teeth: int = 80,
        expected_valid: bool = True,
        expected_issue_codes: tuple[str, ...] = (),
    ) -> ValidatorCase:
        driven_module = module_driver if module_driven is None else module_driven
        center_distance = (module_driver * driver_teeth + driven_module * driven_teeth) / 2.0 + center_offset_mm
        stages = (
            GearStage("input", Point2D(0, 0), (driver_teeth,), module_driver, (driver_layer,)),
            GearStage("output", Point2D(center_distance, 0), (driven_teeth,), driven_module, (driven_layer,)),
        )
        problem = DesignProblem(
            boundary or self.BOUNDARY,
            "input",
            "output",
            DesignConstraints(
                -driver_teeth / driven_teeth if target is None else target,
                min_teeth=min_teeth,
                max_teeth=max_teeth,
            ),
        )
        return ValidatorCase(
            case_id,
            family,
            problem,
            GearTrain(stages, (MeshEdge("input", 0, "output", 0),)),
            expected_valid,
            expected_issue_codes,
        )

    def compound(self, case_id: str, teeth: tuple[int, int, int, int]) -> ValidatorCase:
        input_teeth, first_compound, second_compound, output_teeth = teeth
        compound_x = (input_teeth + first_compound) / 2.0
        output_x = compound_x + (second_compound + output_teeth) / 2.0
        train = GearTrain(
            (
                GearStage("input", Point2D(0, 0), (input_teeth,), 1.0, (0,)),
                GearStage("compound", Point2D(compound_x, 0), (first_compound, second_compound), 1.0, (0, 1)),
                GearStage("output", Point2D(output_x, 0), (output_teeth,), 1.0, (1,)),
            ),
            (MeshEdge("input", 0, "compound", 0), MeshEdge("compound", 1, "output", 0)),
        )
        ratio = input_teeth / first_compound * second_compound / output_teeth
        problem = DesignProblem(self.BOUNDARY, "input", "output", DesignConstraints(ratio, min_teeth=18, max_teeth=80))
        return ValidatorCase(case_id, "compound-valid", problem, train, True)


class ValidatorCaseCatalog:
    """Fifty explicitly named cases across ten independent invariant families."""

    VERSION = "certified-planar-v2-curated-50"

    def __init__(self, builder: ValidatorCaseBuilder | None = None):
        self._builder = builder or ValidatorCaseBuilder()

    def cases(self) -> tuple[ValidatorCase, ...]:
        cases = (
            *self._simple_valid(),
            *self._compound_valid(),
            *self._ratio_mismatch(),
            *self._center_distance(),
            *self._boundary_clearance(),
            *self._unintended_collision(),
            *self._axial_mismatch(),
            *self._tooth_rules(),
            *self._module_mismatch(),
            *self._graph_integrity(),
        )
        if len(cases) != 50 or len({case.case_id for case in cases}) != 50:
            raise RuntimeError("Validator corpus must contain 50 unique cases")
        return cases

    def _simple_valid(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.simple(case_id, "simple-valid", first, second)
            for case_id, first, second in (
                ("simple-valid-equal", 20, 20),
                ("simple-valid-reduction", 18, 24),
                ("simple-valid-increase", 24, 18),
                ("simple-valid-large", 30, 45),
                ("simple-valid-three-two", 22, 33),
            )
        )

    def _compound_valid(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.compound(case_id, teeth)
            for case_id, teeth in (
                ("compound-valid-unit", (20, 20, 20, 20)),
                ("compound-valid-four-three", (20, 20, 40, 30)),
                ("compound-valid-three-four", (18, 24, 20, 20)),
                ("compound-valid-five-four", (25, 20, 24, 24)),
                ("compound-valid-nine-ten", (18, 20, 27, 27)),
            )
        )

    def _ratio_mismatch(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.simple(case_id, "ratio-mismatch", first, second, target=target, expected_valid=False, expected_issue_codes=("speed_ratio_mismatch",))
            for case_id, first, second, target in (
                ("ratio-wrong-sign", 20, 20, 1.0),
                ("ratio-wrong-unit", 18, 24, -1.0),
                ("ratio-wrong-half", 24, 18, -0.5),
                ("ratio-wrong-double", 30, 20, -3.0),
                ("ratio-wrong-near", 22, 33, -0.65),
            )
        )

    def _center_distance(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.simple(case_id, "center-distance", 20 + index, 20 + index, center_offset_mm=offset, expected_valid=False, expected_issue_codes=("mesh_center_distance",))
            for index, (case_id, offset) in enumerate(
                (("center-expanded", 1.0), ("center-compressed", -1.0), ("center-expanded-small", 0.1), ("center-compressed-small", -0.1), ("center-expanded-large", 5.0))
            )
        )

    def _boundary_clearance(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.simple(
                case_id,
                "boundary-clearance",
                teeth,
                teeth,
                boundary=(Point2D(-extent, -extent), Point2D(extent, -extent), Point2D(extent, extent), Point2D(-extent, extent)),
                expected_valid=False,
                expected_issue_codes=("boundary_clearance",),
            )
            for case_id, teeth, extent in (
                ("boundary-tight-20", 20, 25),
                ("boundary-tight-22", 22, 27),
                ("boundary-tight-24", 24, 29),
                ("boundary-tight-26", 26, 31),
                ("boundary-tight-28", 28, 33),
            )
        )

    def _unintended_collision(self) -> tuple[ValidatorCase, ...]:
        cases = []
        for index, x in enumerate((2.0, 4.0, 6.0, 8.0, 10.0), 1):
            base = self._builder.simple(f"collision-{index:02d}", "unintended-collision", 20, 20)
            idle = GearStage("idle", Point2D(x, 0), (20,), 1.0, (0,))
            cases.append(ValidatorCase(base.case_id, base.family, base.problem, GearTrain((*base.train.stages, idle), base.train.meshes), False, ("stage_collision",)))
        return tuple(cases)

    def _axial_mismatch(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.simple(case_id, "axial-mismatch", teeth, teeth, driver_layer=0, driven_layer=layer, expected_valid=False, expected_issue_codes=("axial_layer_mismatch",))
            for case_id, teeth, layer in (
                ("axial-layer-1", 20, 1),
                ("axial-layer-2", 22, 2),
                ("axial-layer-3", 24, 3),
                ("axial-layer-4", 26, 4),
                ("axial-layer-5", 28, 5),
            )
        )

    def _tooth_rules(self) -> tuple[ValidatorCase, ...]:
        return (
            self._builder.simple("teeth-below-declared", "tooth-rules", 18, 18, min_teeth=20, expected_valid=False, expected_issue_codes=("tooth_count_out_of_bounds",)),
            self._builder.simple("teeth-above-declared", "tooth-rules", 81, 81, max_teeth=80, expected_valid=False, expected_issue_codes=("tooth_count_out_of_bounds",)),
            self._builder.simple("teeth-undercut-16", "tooth-rules", 16, 16, min_teeth=10, expected_valid=False, expected_issue_codes=("standard_undercut_risk",)),
            self._builder.simple("teeth-undercut-15", "tooth-rules", 15, 20, min_teeth=10, expected_valid=False, expected_issue_codes=("standard_undercut_risk",)),
            self._builder.simple("teeth-undercut-pair", "tooth-rules", 14, 14, min_teeth=10, expected_valid=False, expected_issue_codes=("standard_undercut_risk",)),
        )

    def _module_mismatch(self) -> tuple[ValidatorCase, ...]:
        return tuple(
            self._builder.simple(case_id, "module-mismatch", 20, 20, module_driver=first, module_driven=second, expected_valid=False, expected_issue_codes=("mesh_module_mismatch",))
            for case_id, first, second in (
                ("module-1-v-1p25", 1.0, 1.25),
                ("module-1-v-1p5", 1.0, 1.5),
                ("module-1p25-v-2", 1.25, 2.0),
                ("module-2-v-1", 2.0, 1.0),
                ("module-2-v-2p5", 2.0, 2.5),
            )
        )

    def _graph_integrity(self) -> tuple[ValidatorCase, ...]:
        base = self._builder.simple("graph-base", "graph-integrity", 20, 20)
        edge = base.train.meshes[0]
        return (
            ValidatorCase("graph-disconnected", "graph-integrity", base.problem, GearTrain(base.train.stages, ()), False, ("disconnected_output",)),
            ValidatorCase("graph-duplicate", "graph-integrity", base.problem, GearTrain(base.train.stages, (edge, edge)), False, ("duplicate_mesh",)),
            ValidatorCase("graph-member-index", "graph-integrity", base.problem, GearTrain(base.train.stages, (MeshEdge("input", 1, "output", 0),)), False, ("mesh_member_index",)),
            ValidatorCase("graph-missing-stage", "graph-integrity", base.problem, GearTrain(base.train.stages, (MeshEdge("input", 0, "ghost", 0),)), False, ("mesh_missing_stage",)),
            ValidatorCase("graph-missing-terminal", "graph-integrity", base.problem, GearTrain((base.train.stages[0], GearStage("other", Point2D(60, 0), (20,), 1.0)), ()), False, ("missing_terminal_stage",)),
        )


class AnalyticalCorpusAuditor:
    """Independently confirm the targeted construction behind each expected label."""

    def audit(self, case: ValidatorCase) -> bool:
        checks = {
            "simple-valid": self._valid_simple,
            "compound-valid": self._valid_compound,
            "ratio-mismatch": self._ratio_mismatch,
            "center-distance": self._center_mismatch,
            "boundary-clearance": self._boundary_violation,
            "unintended-collision": self._collision,
            "axial-mismatch": self._axial_mismatch,
            "tooth-rules": self._tooth_violation,
            "module-mismatch": self._module_mismatch,
            "graph-integrity": self._graph_violation,
        }
        return checks[case.family](case)

    @staticmethod
    def _valid_simple(case: ValidatorCase) -> bool:
        first, second = case.train.stages
        edge = case.train.meshes[0]
        distance = hypot(first.center.x - second.center.x, first.center.y - second.center.y)
        expected = first.pitch_radius_mm(edge.driver_member) + second.pitch_radius_mm(edge.driven_member)
        return isclose(distance, expected) and isclose(case.problem.constraints.target_speed_ratio, -first.teeth[0] / second.teeth[0])

    @staticmethod
    def _valid_compound(case: ValidatorCase) -> bool:
        first, compound, output = case.train.stages
        ratio = first.teeth[0] / compound.teeth[0] * compound.teeth[1] / output.teeth[0]
        return isclose(ratio, case.problem.constraints.target_speed_ratio) and compound.axial_layers == (0, 1)

    @staticmethod
    def _ratio_mismatch(case: ValidatorCase) -> bool:
        first, second = case.train.stages
        return not isclose(case.problem.constraints.target_speed_ratio, -first.teeth[0] / second.teeth[0], rel_tol=1e-6, abs_tol=1e-6)

    @staticmethod
    def _center_mismatch(case: ValidatorCase) -> bool:
        first, second = case.train.stages
        actual = hypot(first.center.x - second.center.x, first.center.y - second.center.y)
        return not isclose(actual, first.pitch_radius_mm(0) + second.pitch_radius_mm(0), abs_tol=1e-6)

    @staticmethod
    def _boundary_violation(case: ValidatorCase) -> bool:
        extent = max(point.x for point in case.problem.boundary)
        return any(abs(stage.center.x) + stage.outer_radius_mm() > extent for stage in case.train.stages)

    @staticmethod
    def _collision(case: ValidatorCase) -> bool:
        input_stage = case.train.stage_map()["input"]
        idle = case.train.stage_map()["idle"]
        distance = hypot(input_stage.center.x - idle.center.x, input_stage.center.y - idle.center.y)
        return distance < input_stage.outer_radius_mm() + idle.outer_radius_mm()

    @staticmethod
    def _axial_mismatch(case: ValidatorCase) -> bool:
        edge = case.train.meshes[0]
        stages = case.train.stage_map()
        return stages[edge.driver_stage_id].layer(edge.driver_member) != stages[edge.driven_stage_id].layer(edge.driven_member)

    @staticmethod
    def _tooth_violation(case: ValidatorCase) -> bool:
        constraints = case.problem.constraints
        minimum_unshifted = ceil(2.0 / sin(radians(constraints.pressure_angle_deg)) ** 2)
        teeth = [value for stage in case.train.stages for value in stage.teeth]
        return any(value < constraints.min_teeth or value > constraints.max_teeth or value < minimum_unshifted for value in teeth)

    @staticmethod
    def _module_mismatch(case: ValidatorCase) -> bool:
        first, second = case.train.stages
        return not isclose(first.module_mm, second.module_mm)

    @staticmethod
    def _graph_violation(case: ValidatorCase) -> bool:
        stage_ids = set(case.train.stage_map())
        if case.problem.output_stage_id not in stage_ids:
            return True
        seen = set()
        for edge in case.train.meshes:
            key = (edge.driver_stage_id, edge.driver_member, edge.driven_stage_id, edge.driven_member)
            if key in seen or edge.driver_stage_id not in stage_ids or edge.driven_stage_id not in stage_ids:
                return True
            seen.add(key)
            driver = case.train.stage_map()[edge.driver_stage_id]
            driven = case.train.stage_map()[edge.driven_stage_id]
            if edge.driver_member >= len(driver.teeth) or edge.driven_member >= len(driven.teeth):
                return True
        return not case.train.meshes


class ValidatorCorpusRunner:
    """Require analytical construction and production certificate agreement."""

    def __init__(self, auditor: AnalyticalCorpusAuditor | None = None):
        self._auditor = auditor or AnalyticalCorpusAuditor()

    def evaluate(self, cases: tuple[ValidatorCase, ...]) -> tuple[dict, ...]:
        records = []
        for case in cases:
            if not self._auditor.audit(case):
                raise AssertionError(f"Analytical construction failed for {case.case_id}")
            certificate = ReferenceVerifier.verify(case.problem, case.train)
            actual_codes = {issue.code for issue in certificate.issues}
            if certificate.valid != case.expected_valid or not set(case.expected_issue_codes).issubset(actual_codes):
                raise AssertionError(
                    f"Verifier disagreement for {case.case_id}: valid={certificate.valid}, issues={sorted(actual_codes)}"
                )
            records.append(
                {
                    "case_id": case.case_id,
                    "family": case.family,
                    "expected_valid": case.expected_valid,
                    "expected_issue_codes": list(case.expected_issue_codes),
                    "analytical_audit_passed": True,
                    "certificate": certificate.to_json(),
                }
            )
        return tuple(records)


class ValidatorCorpusFreezer:
    """Freeze per-case certificates and a content-addressed corpus index."""

    def freeze(self, records: tuple[dict, ...], root: str | Path) -> Path:
        destination = Path(root)
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Validator corpus destination must be empty")
        records_root = destination / "cases"
        records_root.mkdir(parents=True)
        index_records = []
        for record in records:
            payload = self._encode(record)
            (records_root / f"{record['case_id']}.json").write_bytes(payload)
            index_records.append({"case_id": record["case_id"], "sha256": hashlib.sha256(payload).hexdigest()})
        index = {
            "dataset_id": ValidatorCaseCatalog.VERSION,
            "case_count": len(records),
            "valid_count": sum(record["expected_valid"] for record in records),
            "invalid_count": sum(not record["expected_valid"] for record in records),
            "all_analytical_audits_passed": all(record["analytical_audit_passed"] for record in records),
            "cases": index_records,
        }
        index_path = destination / "index.json"
        index_path.write_bytes(self._encode(index))
        return index_path

    @staticmethod
    def _encode(value: dict) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


@dataclass(frozen=True)
class FrozenValidatorCorpus:
    dataset_id: str
    records: tuple[dict, ...]
    corpus_sha256: str


class ValidatorCorpusLoader:
    """Verify all corpus bytes and semantic gates before exposing records."""

    def load(self, root: str | Path) -> FrozenValidatorCorpus:
        source = Path(root)
        index_bytes = (source / "index.json").read_bytes()
        index = json.loads(index_bytes)
        aggregate = hashlib.sha256(index_bytes)
        records = []
        identifiers = set()
        for item in index["cases"]:
            case_id = item["case_id"]
            if case_id in identifiers:
                raise ValueError(f"Duplicate validator corpus id: {case_id}")
            identifiers.add(case_id)
            payload = (source / "cases" / f"{case_id}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise ValueError(f"Validator corpus hash mismatch: {case_id}")
            aggregate.update(payload)
            record = json.loads(payload)
            if not record["analytical_audit_passed"]:
                raise ValueError(f"Analytical audit did not pass: {case_id}")
            if record["certificate"]["model_version"] != "certified-planar-v2":
                raise ValueError(f"Unexpected verifier model version: {case_id}")
            records.append(record)
        if len(records) != index["case_count"]:
            raise ValueError("Validator corpus count mismatch")
        actual_valid = sum(record["expected_valid"] for record in records)
        if actual_valid != index["valid_count"] or len(records) - actual_valid != index["invalid_count"]:
            raise ValueError("Validator corpus validity counts do not match")
        return FrozenValidatorCorpus(index["dataset_id"], tuple(records), aggregate.hexdigest())
