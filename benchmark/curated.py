"""Hand-authored requirements-first cases and separated evidence freezing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from benchmark.oracle import ExactCompoundTrainOracle, GroundTruthOracle
from benchmark.specification import (
    DesignSpace,
    PrescribedShaft,
    ProblemSpecification,
    RequirementsFirstBenchmarkCase,
    SolverBenchmarkView,
    SolverPayloadGuard,
)
from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MeshEdge, Point2D
from synthesis.requirements_solver import ProductionCandidateValidator


@dataclass(frozen=True)
class CuratedCaseDefinition:
    """One independently specified analytical or adversarial design brief."""

    case_id: str
    category: str
    terminal_distance_mm: float
    target_ratio: float
    boundary_half_extent_mm: float = 60.0
    boundary_clearance_mm: float = 0.0
    obstacle: tuple[Point2D, ...] | None = None


class CuratedCaseCatalog:
    """Versioned catalog of 50 explicit, reviewable benchmark definitions."""

    VERSION = "curated-compound-50-v2"

    def definitions(self) -> tuple[CuratedCaseDefinition, ...]:
        feasible = (
            CuratedCaseDefinition("valid-unit-30", "analytical-feasible", 30.0, 1.0),
            CuratedCaseDefinition("valid-up-32", "analytical-feasible", 32.0, 1.2),
            CuratedCaseDefinition("valid-down-34", "analytical-feasible", 34.0, 0.8),
            CuratedCaseDefinition("valid-high-35", "analytical-feasible", 35.0, 1.5),
            CuratedCaseDefinition("valid-low-31", "analytical-feasible", 31.0, 2.0 / 3.0),
            CuratedCaseDefinition("valid-five-four-36", "analytical-feasible", 36.0, 1.25),
            CuratedCaseDefinition("valid-three-four-33", "analytical-feasible", 33.0, 0.75),
            CuratedCaseDefinition("valid-four-three-37", "analytical-feasible", 37.0, 4.0 / 3.0),
            CuratedCaseDefinition("valid-nine-ten-30", "analytical-feasible", 30.0, 0.9),
            CuratedCaseDefinition("valid-eleven-ten-38", "analytical-feasible", 38.0, 1.1),
        )
        ratio_infeasible = tuple(
            CuratedCaseDefinition(case_id, "ratio-infeasible", distance, ratio)
            for case_id, distance, ratio in (
                ("ratio-none-01", 30.0, 1.001001),
                ("ratio-none-02", 31.0, 1.003003),
                ("ratio-none-03", 32.0, 1.007007),
                ("ratio-none-04", 33.0, 1.011011),
                ("ratio-none-05", 34.0, 1.013013),
                ("ratio-none-06", 35.0, 1.017017),
                ("ratio-none-07", 36.0, 1.019019),
                ("ratio-none-08", 37.0, 1.023023),
                ("ratio-none-09", 38.0, 1.029029),
                ("ratio-none-10", 39.0, 1.031031),
            )
        )
        spacing_infeasible = tuple(
            CuratedCaseDefinition(f"spacing-none-{index:02d}", "shaft-spacing-infeasible", distance, 1.0)
            for index, distance in enumerate((60.0, 62.0, 64.0, 66.0, 68.0, 70.0, 72.0, 74.0, 76.0, 78.0), 1)
        )
        obstacle = (Point2D(5, -30), Point2D(25, -30), Point2D(25, 30), Point2D(5, 30))
        obstacle_infeasible = tuple(
            CuratedCaseDefinition(f"obstacle-none-{index:02d}", "obstacle-infeasible", distance, 1.0, obstacle=obstacle)
            for index, distance in enumerate((28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0), 1)
        )
        boundary_infeasible = tuple(
            CuratedCaseDefinition(
                f"boundary-none-{index:02d}",
                "boundary-infeasible",
                distance,
                1.0,
                boundary_half_extent_mm=extent,
                boundary_clearance_mm=clearance,
            )
            for index, (distance, extent, clearance) in enumerate(
                (
                    (30.0, 35.0, 8.0),
                    (31.0, 36.0, 9.0),
                    (32.0, 37.0, 10.0),
                    (33.0, 38.0, 11.0),
                    (34.0, 39.0, 12.0),
                    (35.0, 40.0, 13.0),
                    (36.0, 41.0, 14.0),
                    (37.0, 42.0, 15.0),
                    (38.0, 43.0, 16.0),
                    (39.0, 44.0, 17.0),
                ),
                1,
            )
        )
        definitions = (*feasible, *ratio_infeasible, *spacing_infeasible, *obstacle_infeasible, *boundary_infeasible)
        if len(definitions) != 50 or len({definition.case_id for definition in definitions}) != 50:
            raise RuntimeError("The curated catalog must contain 50 unique cases")
        return definitions


class CuratedRequirementsFirstFactory:
    """Convert the explicit catalog into solver views and independent evidence."""

    def __init__(self, oracle: GroundTruthOracle, catalog: CuratedCaseCatalog | None = None):
        self._oracle = oracle
        self._catalog = catalog or CuratedCaseCatalog()
        self._guard = SolverPayloadGuard()

    def build(self) -> tuple[RequirementsFirstBenchmarkCase, ...]:
        cases = []
        for definition in self._catalog.definitions():
            view = self._view(definition)
            self._guard.validate(view.to_json())
            cases.append(RequirementsFirstBenchmarkCase(view, self._oracle.solve(view).to_evidence()))
        return tuple(cases)

    def _view(self, definition: CuratedCaseDefinition) -> SolverBenchmarkView:
        extent = definition.boundary_half_extent_mm
        boundary = (
            Point2D(-extent, -extent),
            Point2D(extent, -extent),
            Point2D(extent, extent),
            Point2D(-extent, extent),
        )
        problem = DesignProblem(
            boundary,
            "input",
            "output",
            DesignConstraints(
                definition.target_ratio,
                ratio_tolerance=1e-9,
                boundary_clearance=definition.boundary_clearance_mm,
                min_teeth=18,
                max_teeth=26,
            ),
        )
        specification = ProblemSpecification(
            "requirements-first-v1",
            problem,
            DesignSpace((1.0,), 3, 3),
            (
                PrescribedShaft("input", Point2D(0, 0)),
                PrescribedShaft("output", Point2D(definition.terminal_distance_mm, 0)),
            ),
            (definition.obstacle,) if definition.obstacle else (),
        )
        return SolverBenchmarkView(definition.case_id, self._catalog.VERSION, "curated", specification)


class CuratedBenchmarkFreezer:
    """Freeze solver inputs and evaluator evidence in physically separate roots."""

    def freeze(self, cases: tuple[RequirementsFirstBenchmarkCase, ...], root: str | Path) -> Path:
        destination = Path(root)
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Curated benchmark destination must be empty")
        solver_root = destination / "solver-inputs"
        evidence_root = destination / "evaluator-only"
        solver_root.mkdir(parents=True)
        evidence_root.mkdir()
        records = []
        for case in cases:
            solver_payload = self._encode(case.solver_payload())
            evidence_payload = self._encode(case.evidence_payload())
            (solver_root / f"{case.solver_view.instance_id}.json").write_bytes(solver_payload)
            (evidence_root / f"{case.solver_view.instance_id}.json").write_bytes(evidence_payload)
            records.append(
                {
                    "instance_id": case.solver_view.instance_id,
                    "solver_sha256": hashlib.sha256(solver_payload).hexdigest(),
                    "evidence_sha256": hashlib.sha256(evidence_payload).hexdigest(),
                }
            )
        index = {
            "dataset_id": CuratedCaseCatalog.VERSION,
            "instance_count": len(cases),
            "feasible_count": sum(case.evidence.expected_feasible for case in cases),
            "infeasible_count": sum(not case.evidence.expected_feasible for case in cases),
            "all_labels_globally_proven": all(case.evidence.globally_proven for case in cases),
            "instances": records,
        }
        index_path = destination / "index.json"
        index_path.write_bytes(self._encode(index))
        return index_path

    @staticmethod
    def _encode(value: dict) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


@dataclass(frozen=True)
class FrozenCuratedDataset:
    """Verified dataset metadata with deliberately separated payload sets."""

    dataset_id: str
    solver_payloads: tuple[dict, ...]
    evidence_payloads: tuple[dict, ...]
    dataset_sha256: str


class FrozenGroundTruthEvidenceVerifier:
    """Recompute frozen labels and validate constructive witnesses on load."""

    def __init__(
        self,
        oracle: GroundTruthOracle | None = None,
        candidate_validator: ProductionCandidateValidator | None = None,
    ) -> None:
        self._oracle = oracle or ExactCompoundTrainOracle()
        self._candidate_validator = candidate_validator or ProductionCandidateValidator()

    def verify(self, solver_payload: dict, evidence_payload: dict) -> None:
        view = SolverBenchmarkView.from_json(solver_payload)
        if evidence_payload["instance_id"] != view.instance_id:
            raise ValueError(f"Curated evidence instance mismatch: {view.instance_id}")
        observed = self._oracle.solve(view)
        expected_feasible = bool(evidence_payload["expected_feasible"])
        if observed.proof.feasible != expected_feasible:
            raise ValueError(f"Curated recomputed label mismatch: {view.instance_id}")
        if observed.proof.to_json() != evidence_payload.get("certificate"):
            raise ValueError(f"Curated oracle certificate mismatch: {view.instance_id}")
        expected_kind = "constructive-witness" if expected_feasible else "exhaustive-proof"
        if evidence_payload.get("proof_kind") != expected_kind:
            raise ValueError(f"Curated proof kind mismatch: {view.instance_id}")
        if evidence_payload.get("oracle_version") != observed.proof.oracle_version:
            raise ValueError(f"Curated oracle version mismatch: {view.instance_id}")
        if expected_feasible:
            train = self._train(evidence_payload.get("reference_train"))
            if not self._candidate_validator.validate(view.specification, train).valid:
                raise ValueError(f"Curated constructive witness is invalid: {view.instance_id}")
        elif evidence_payload.get("reference_train") is not None or not observed.proof.design_space_complete:
            raise ValueError(f"Curated negative proof is incomplete: {view.instance_id}")

    @staticmethod
    def _train(payload: dict | None) -> GearTrain:
        if payload is None:
            raise ValueError("Curated feasible evidence requires a reference train")
        stages = tuple(
            GearStage(
                item["id"],
                Point2D.from_json(item["center"]),
                tuple(item["teeth"]),
                item["module_mm"],
                tuple(item.get("axial_layers", ())),
            )
            for item in payload["stages"]
        )
        return GearTrain(stages, tuple(MeshEdge(**item) for item in payload["meshes"]))


class CuratedBenchmarkLoader:
    """Verify every frozen curated payload before exposing either partition."""

    def __init__(self, evidence_verifier: FrozenGroundTruthEvidenceVerifier | None = None) -> None:
        self._evidence_verifier = evidence_verifier or FrozenGroundTruthEvidenceVerifier()

    def load(self, root: str | Path) -> FrozenCuratedDataset:
        source = Path(root)
        index_bytes = (source / "index.json").read_bytes()
        index = json.loads(index_bytes)
        solver_payloads = []
        evidence_payloads = []
        aggregate = hashlib.sha256(index_bytes)
        identifiers: set[str] = set()
        for record in index["instances"]:
            instance_id = record["instance_id"]
            if instance_id in identifiers:
                raise ValueError(f"Duplicate curated instance id: {instance_id}")
            identifiers.add(instance_id)
            solver_bytes = (source / "solver-inputs" / f"{instance_id}.json").read_bytes()
            evidence_bytes = (source / "evaluator-only" / f"{instance_id}.json").read_bytes()
            self._require_hash(instance_id, "solver", solver_bytes, record["solver_sha256"])
            self._require_hash(instance_id, "evidence", evidence_bytes, record["evidence_sha256"])
            aggregate.update(solver_bytes)
            aggregate.update(evidence_bytes)
            solver_payload = json.loads(solver_bytes)
            evidence_payload = json.loads(evidence_bytes)
            self._evidence_verifier.verify(solver_payload, evidence_payload)
            solver_payloads.append(solver_payload)
            evidence_payloads.append(evidence_payload)
        if len(identifiers) != index["instance_count"]:
            raise ValueError("Curated benchmark instance count mismatch")
        if not index["all_labels_globally_proven"]:
            raise ValueError("Curated publication data requires globally proven labels")
        actual_feasible = sum(bool(payload["expected_feasible"]) for payload in evidence_payloads)
        if actual_feasible != index["feasible_count"] or len(evidence_payloads) - actual_feasible != index["infeasible_count"]:
            raise ValueError("Curated benchmark label counts do not match the index")
        return FrozenCuratedDataset(
            index["dataset_id"],
            tuple(solver_payloads),
            tuple(evidence_payloads),
            aggregate.hexdigest(),
        )

    @staticmethod
    def _require_hash(instance_id: str, kind: str, payload: bytes, expected: str) -> None:
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f"Curated {kind} hash mismatch: {instance_id}")


class SolverInputDirectoryLoader:
    """Load typed blind inputs without resolving or reading a parent directory."""

    def __init__(self, guard: SolverPayloadGuard | None = None):
        self._guard = guard or SolverPayloadGuard()

    def load(self, solver_input_root: str | Path) -> tuple[SolverBenchmarkView, ...]:
        root = Path(solver_input_root)
        views = []
        for path in sorted(root.glob("*.json")):
            payload = json.loads(path.read_bytes())
            self._guard.validate(payload)
            view = SolverBenchmarkView.from_json(payload)
            if view.instance_id != path.stem:
                raise ValueError(f"Solver input filename/id mismatch: {path.name}")
            views.append(view)
        if not views:
            raise ValueError("A blind synthesis run requires solver input files")
        if len({view.instance_id for view in views}) != len(views):
            raise ValueError("Blind solver inputs must have unique ids")
        return tuple(views)
