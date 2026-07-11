"""Requirements-first benchmark contracts with an explicit evidence boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

from common.design_models import DesignProblem, GearTrain, Point2D


@dataclass(frozen=True)
class PrescribedShaft:
    """A shaft location fixed by an engineering design brief."""

    role: str
    center: Point2D

    def __post_init__(self) -> None:
        if self.role not in {"input", "output"}:
            raise ValueError("A prescribed shaft role must be input or output")
        if not isfinite(self.center.x) or not isfinite(self.center.y):
            raise ValueError("Prescribed shaft coordinates must be finite")


@dataclass(frozen=True)
class DesignSpace:
    """Bounded decisions available to every synthesis method."""

    allowed_modules_mm: tuple[float, ...]
    minimum_stage_count: int
    maximum_stage_count: int
    maximum_compound_members: int = 2
    axial_layer_count: int = 2

    def __post_init__(self) -> None:
        if not self.allowed_modules_mm or any(not isfinite(value) or value <= 0 for value in self.allowed_modules_mm):
            raise ValueError("Allowed modules must be finite and positive")
        if len(set(self.allowed_modules_mm)) != len(self.allowed_modules_mm):
            raise ValueError("Allowed modules must be unique")
        if self.minimum_stage_count < 2 or self.maximum_stage_count < self.minimum_stage_count:
            raise ValueError("Invalid stage-count bounds")
        if self.maximum_compound_members < 1 or self.axial_layer_count < 1:
            raise ValueError("Compound-member and axial-layer limits must be positive")


@dataclass(frozen=True)
class ProblemSpecification:
    """Solver-visible engineering requirements, never a constructed answer."""

    schema_version: str
    problem: DesignProblem
    design_space: DesignSpace
    prescribed_shafts: tuple[PrescribedShaft, ...]
    obstacles: tuple[tuple[Point2D, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != "requirements-first-v1":
            raise ValueError("Unsupported problem specification schema")
        roles = [shaft.role for shaft in self.prescribed_shafts]
        if sorted(roles) != ["input", "output"]:
            raise ValueError("Exactly one input and one output shaft must be prescribed")
        if any(len(polygon) < 3 for polygon in self.obstacles):
            raise ValueError("Every obstacle must be a polygon")

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SolverBenchmarkView:
    """The complete object a solver may receive during blind evaluation."""

    instance_id: str
    family: str
    partition: str
    specification: ProblemSpecification

    def to_json(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "family": self.family,
            "partition": self.partition,
            "specification": self.specification.to_json(),
        }


@dataclass(frozen=True)
class GroundTruthEvidence:
    """Evaluator-only evidence kept outside the solver-facing record."""

    expected_feasible: bool
    proof_kind: str
    oracle_version: str
    reference_train: GearTrain | None = None
    certificate: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        allowed = {"constructive-witness", "exhaustive-proof", "exact-solver-proof", "unknown"}
        if self.proof_kind not in allowed:
            raise ValueError(f"Unsupported proof kind: {self.proof_kind}")
        if self.expected_feasible and self.reference_train is None:
            raise ValueError("A feasible label requires a constructive witness")
        if not self.expected_feasible and self.proof_kind == "constructive-witness":
            raise ValueError("A negative label cannot use a constructive-witness proof")

    @property
    def globally_proven(self) -> bool:
        if self.expected_feasible:
            return self.reference_train is not None and self.certificate is not None
        return self.proof_kind in {"exhaustive-proof", "exact-solver-proof"}


@dataclass(frozen=True)
class RequirementsFirstBenchmarkCase:
    """Aggregate root whose public view cannot serialize evaluator evidence."""

    solver_view: SolverBenchmarkView
    evidence: GroundTruthEvidence

    def solver_payload(self) -> dict[str, Any]:
        return self.solver_view.to_json()

    def evidence_payload(self) -> dict[str, Any]:
        return {
            "instance_id": self.solver_view.instance_id,
            "expected_feasible": self.evidence.expected_feasible,
            "proof_kind": self.evidence.proof_kind,
            "oracle_version": self.evidence.oracle_version,
            "reference_train": self.evidence.reference_train.to_json() if self.evidence.reference_train else None,
            "certificate": self.evidence.certificate,
        }


class SolverPayloadGuard:
    """Fail closed when evaluator-only fields cross the solver boundary."""

    _FORBIDDEN_KEYS = frozenset({"reference_train", "certificate", "expected_feasible", "proof_kind", "oracle_version"})

    def validate(self, payload: dict[str, Any]) -> None:
        forbidden = self._find_forbidden(payload)
        if forbidden:
            raise ValueError(f"Solver payload contains evaluator-only fields: {', '.join(sorted(forbidden))}")

    def _find_forbidden(self, value: Any) -> set[str]:
        if isinstance(value, dict):
            found = set(self._FORBIDDEN_KEYS.intersection(value))
            for child in value.values():
                found.update(self._find_forbidden(child))
            return found
        if isinstance(value, (list, tuple)):
            found: set[str] = set()
            for child in value:
                found.update(self._find_forbidden(child))
            return found
        return set()
