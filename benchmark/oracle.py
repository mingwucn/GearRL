"""Independent exact oracle for bounded requirements-first benchmark labels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import json
from math import ceil, cos, hypot, isclose, pi, radians, sin, sqrt
from typing import Any

from benchmark.specification import GroundTruthEvidence, SolverBenchmarkView
from common.design_models import GearStage, GearTrain, MeshEdge, Point2D


@dataclass(frozen=True)
class OracleProof:
    """Machine-readable account of a bounded exact-oracle decision."""

    oracle_version: str
    feasible: bool
    evaluated_parameter_tuples: int
    evaluated_placements: int
    design_space_complete: bool
    reason: str
    elimination_ledger: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        payload = {
            "oracle_version": self.oracle_version,
            "feasible": self.feasible,
            "evaluated_parameter_tuples": self.evaluated_parameter_tuples,
            "evaluated_placements": self.evaluated_placements,
            "design_space_complete": self.design_space_complete,
            "reason": self.reason,
        }
        if self.elimination_ledger is not None:
            payload["elimination_ledger"] = self.elimination_ledger
        return payload

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "OracleProof":
        return cls(
            oracle_version=str(payload["oracle_version"]),
            feasible=bool(payload["feasible"]),
            evaluated_parameter_tuples=int(payload["evaluated_parameter_tuples"]),
            evaluated_placements=int(payload["evaluated_placements"]),
            design_space_complete=bool(payload["design_space_complete"]),
            reason=str(payload["reason"]),
            elimination_ledger=payload.get("elimination_ledger"),
        )


@dataclass(frozen=True)
class OracleResult:
    """Exact-oracle result with an optional constructive witness."""

    proof: OracleProof
    witness: GearTrain | None

    def to_evidence(self) -> GroundTruthEvidence:
        proof_kind = "constructive-witness" if self.proof.feasible else "exhaustive-proof"
        return GroundTruthEvidence(
            expected_feasible=self.proof.feasible,
            proof_kind=proof_kind,
            oracle_version=self.proof.oracle_version,
            reference_train=self.witness,
            certificate=self.proof.to_json(),
        )


class GroundTruthOracle(ABC):
    """Evaluator-only strategy for establishing benchmark truth."""

    @abstractmethod
    def solve(self, view: SolverBenchmarkView) -> OracleResult:
        """Return a constructive witness or a complete bounded-domain proof."""


class OracleSearchLedger(ABC):
    """Observer contract for a replayable account of every bounded tuple."""

    @abstractmethod
    def record(self, module: float, teeth: tuple[int, int, int, int], disposition: str, placement_count: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def seal(self) -> dict[str, Any]:
        raise NotImplementedError


class NullOracleSearchLedger(OracleSearchLedger):
    def record(self, module: float, teeth: tuple[int, int, int, int], disposition: str, placement_count: int) -> None:
        return None

    def seal(self) -> dict[str, Any]:
        return {}


class HashingOracleSearchLedger(OracleSearchLedger):
    """Hash canonical tuple dispositions while retaining auditable totals."""

    SCHEMA_VERSION = "oracle-elimination-ledger-v1"

    def __init__(self) -> None:
        self._digest = sha256()
        self._counts: dict[str, int] = {}
        self._tuple_count = 0

    def record(self, module: float, teeth: tuple[int, int, int, int], disposition: str, placement_count: int) -> None:
        payload = {"disposition": disposition, "module_mm": module, "placement_count": placement_count, "teeth": teeth}
        self._digest.update((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())
        self._counts[disposition] = self._counts.get(disposition, 0) + 1
        self._tuple_count += 1

    def seal(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "tuple_count": self._tuple_count,
            "disposition_counts": dict(sorted(self._counts.items())),
            "ledger_sha256": self._digest.hexdigest(),
        }


class PlanarGeometryKernel:
    """Independent geometry predicates used only by the exact oracle."""

    @staticmethod
    def circle_intersections(first: Point2D, first_radius: float, second: Point2D, second_radius: float) -> tuple[Point2D, ...]:
        distance = hypot(second.x - first.x, second.y - first.y)
        if distance == 0 or distance > first_radius + second_radius + 1e-9:
            return ()
        if distance < abs(first_radius - second_radius) - 1e-9:
            return ()
        along = (first_radius ** 2 - second_radius ** 2 + distance ** 2) / (2.0 * distance)
        height_squared = first_radius ** 2 - along ** 2
        if height_squared < -1e-9:
            return ()
        height = sqrt(max(0.0, height_squared))
        unit_x = (second.x - first.x) / distance
        unit_y = (second.y - first.y) / distance
        base_x = first.x + along * unit_x
        base_y = first.y + along * unit_y
        offset_x = -unit_y * height
        offset_y = unit_x * height
        first_solution = Point2D(base_x + offset_x, base_y + offset_y)
        if height <= 1e-12:
            return (first_solution,)
        return (first_solution, Point2D(base_x - offset_x, base_y - offset_y))

    @classmethod
    def circle_inside_polygon(cls, center: Point2D, radius: float, polygon: tuple[Point2D, ...]) -> bool:
        return cls._point_inside(center, polygon) and cls._distance_to_polygon(center, polygon) + 1e-9 >= radius

    @classmethod
    def circle_intersects_polygon(cls, center: Point2D, radius: float, polygon: tuple[Point2D, ...]) -> bool:
        return cls._point_inside(center, polygon) or cls._distance_to_polygon(center, polygon) < radius - 1e-9

    @staticmethod
    def _point_inside(point: Point2D, polygon: tuple[Point2D, ...]) -> bool:
        inside = False
        for index, first in enumerate(polygon):
            second = polygon[(index + 1) % len(polygon)]
            if (first.y > point.y) != (second.y > point.y):
                crossing_x = (second.x - first.x) * (point.y - first.y) / (second.y - first.y) + first.x
                if point.x < crossing_x:
                    inside = not inside
        return inside

    @classmethod
    def _distance_to_polygon(cls, point: Point2D, polygon: tuple[Point2D, ...]) -> float:
        return min(
            cls._distance_to_segment(point, polygon[index], polygon[(index + 1) % len(polygon)])
            for index in range(len(polygon))
        )

    @staticmethod
    def _distance_to_segment(point: Point2D, first: Point2D, second: Point2D) -> float:
        dx = second.x - first.x
        dy = second.y - first.y
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            return hypot(point.x - first.x, point.y - first.y)
        projection = max(0.0, min(1.0, ((point.x - first.x) * dx + (point.y - first.y) * dy) / length_squared))
        nearest_x = first.x + projection * dx
        nearest_y = first.y + projection * dy
        return hypot(point.x - nearest_x, point.y - nearest_y)


class ExactCompoundTrainOracle(GroundTruthOracle):
    """Complete enumerator for one two-mesh, three-shaft compound topology.

    This evaluator is deliberately independent of the production verifier. It
    owns a small, explicit design space so a negative outcome is a real proof
    over the declared family rather than a failure to recover a seeded answer.
    """

    VERSION = "exact-compound-oracle-v1"

    def __init__(self, geometry: PlanarGeometryKernel | None = None, ledger: OracleSearchLedger | None = None):
        self._geometry = geometry or PlanarGeometryKernel()
        self._ledger = ledger or NullOracleSearchLedger()

    def solve(self, view: SolverBenchmarkView) -> OracleResult:
        specification = view.specification
        space = specification.design_space
        if space.minimum_stage_count > 3 or space.maximum_stage_count < 3 or space.maximum_compound_members < 2:
            return self._negative(0, 0, "The exact compound topology is excluded by the design space")
        terminals = {shaft.role: shaft.center for shaft in specification.prescribed_shafts}
        constraints = specification.problem.constraints
        parameter_count = 0
        placement_count = 0
        teeth = range(constraints.min_teeth, constraints.max_teeth + 1)
        for module in space.allowed_modules_mm:
            for tooth_tuple in product(teeth, repeat=4):
                parameter_count += 1
                input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
                if not self._standard_mesh_admissible(
                    module,
                    input_teeth,
                    first_compound,
                    constraints.pressure_angle_deg,
                ) or not self._standard_mesh_admissible(
                    module,
                    second_compound,
                    output_teeth,
                    constraints.pressure_angle_deg,
                ):
                    self._ledger.record(module, tooth_tuple, "standard-mesh", 0)
                    continue
                ratio = (input_teeth / first_compound) * (second_compound / output_teeth)
                target = constraints.target_speed_ratio
                if target is not None and not isclose(ratio, target, rel_tol=constraints.ratio_tolerance, abs_tol=constraints.ratio_tolerance):
                    self._ledger.record(module, tooth_tuple, "ratio", 0)
                    continue
                input_distance = module * (input_teeth + first_compound) / 2.0
                output_distance = module * (second_compound + output_teeth) / 2.0
                placements = self._geometry.circle_intersections(terminals["input"], input_distance, terminals["output"], output_distance)
                placement_count += len(placements)
                for compound_center in placements:
                    witness = self._witness(terminals, compound_center, module, tooth_tuple)
                    if self._admissible(specification.problem.boundary, specification.obstacles, constraints.boundary_clearance, witness):
                        self._ledger.record(module, tooth_tuple, "witness", len(placements))
                        proof = OracleProof(self.VERSION, True, parameter_count, placement_count, False, "Constructive witness found")
                        return OracleResult(proof, witness)
                self._ledger.record(module, tooth_tuple, "no-placement" if not placements else "geometry", len(placements))
        return self._negative(parameter_count, placement_count, "Every bounded parameter tuple and geometric placement was eliminated")

    def _negative(self, parameter_count: int, placement_count: int, reason: str) -> OracleResult:
        return OracleResult(OracleProof(self.VERSION, False, parameter_count, placement_count, True, reason), None)


    @staticmethod
    def _standard_mesh_admissible(module: float, first_teeth: int, second_teeth: int, pressure_angle_deg: float) -> bool:
        pressure_angle = radians(pressure_angle_deg)
        if min(first_teeth, second_teeth) < ceil(2.0 / sin(pressure_angle) ** 2):
            return False
        first_pitch = module * first_teeth / 2.0
        second_pitch = module * second_teeth / 2.0
        first_base = first_pitch * cos(pressure_angle)
        second_base = second_pitch * cos(pressure_angle)
        first_addendum = module * (first_teeth + 2) / 2.0
        second_addendum = module * (second_teeth + 2) / 2.0
        path = (
            sqrt(max(0.0, first_addendum ** 2 - first_base ** 2))
            + sqrt(max(0.0, second_addendum ** 2 - second_base ** 2))
            - (first_pitch + second_pitch) * sin(pressure_angle)
        )
        return path / (pi * module * cos(pressure_angle)) + 1e-12 >= 1.0

    @staticmethod
    def _witness(
        terminals: dict[str, Point2D], compound_center: Point2D, module: float, tooth_tuple: tuple[int, int, int, int]
    ) -> GearTrain:
        input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
        return GearTrain(
            stages=(
                GearStage("input", terminals["input"], (input_teeth,), module, (0,)),
                GearStage("compound", compound_center, (first_compound, second_compound), module, (0, 1)),
                GearStage("output", terminals["output"], (output_teeth,), module, (1,)),
            ),
            meshes=(MeshEdge("input", 0, "compound", 0), MeshEdge("compound", 1, "output", 0)),
        )

    def _admissible(
        self,
        boundary: tuple[Point2D, ...],
        obstacles: tuple[tuple[Point2D, ...], ...],
        clearance: float,
        train: GearTrain,
    ) -> bool:
        for stage in train.stages:
            radius = stage.outer_radius_mm() + clearance
            if not self._geometry.circle_inside_polygon(stage.center, radius, boundary):
                return False
            if any(self._geometry.circle_intersects_polygon(stage.center, radius, obstacle) for obstacle in obstacles):
                return False
        return True


class ReplayableExactCompoundTrainOracle(GroundTruthOracle):
    """Produce complete negative proofs with a deterministic elimination ledger."""

    VERSION = "exact-compound-oracle-replay-v1"

    def solve(self, view: SolverBenchmarkView) -> OracleResult:
        ledger = HashingOracleSearchLedger()
        result = ExactCompoundTrainOracle(ledger=ledger).solve(view)
        proof = OracleProof(
            self.VERSION,
            result.proof.feasible,
            result.proof.evaluated_parameter_tuples,
            result.proof.evaluated_placements,
            result.proof.design_space_complete,
            result.proof.reason,
            ledger.seal(),
        )
        return OracleResult(proof, result.witness)


class ReplayableOracleProofVerifier:
    """Replay a solver-visible brief and require the complete proof to match."""

    def verify(self, view: SolverBenchmarkView, expected: OracleProof) -> OracleProof:
        if expected.feasible or not expected.design_space_complete or expected.elimination_ledger is None:
            raise ValueError("Replay verification requires a complete negative elimination proof")
        observed = ReplayableExactCompoundTrainOracle().solve(view).proof
        if observed != expected:
            raise ValueError("Replayable oracle proof mismatch")
        return observed
