"""Blind requirements-first synthesis strategies and injected validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import replace
from itertools import product
import json
from math import hypot, isclose, sqrt
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.optimize import differential_evolution

from benchmark.specification import ProblemSpecification, SolverBenchmarkView
from common.certificate_binding import ValidationCertificateBinder
from common.design_models import CertificateModelIdentity, GearStage, GearTrain, MeshEdge, Point2D, ValidationCertificate
from physics_validator.reference_verifier import ReferenceVerifier
from synthesis.specification_validator import (
    DesignSpaceValidationRule,
    ObstacleValidationRule,
    PrescribedShaftValidationRule,
    ProblemSpecificationValidator,
)


@dataclass(frozen=True)
class RequirementsSynthesisResult:
    """Blind solver outcome with search accounting but no ground-truth fields."""

    train: GearTrain | None
    parameter_tuples_evaluated: int
    placements_evaluated: int
    search_complete: bool
    certificate: ValidationCertificate | None


@dataclass(frozen=True)
class SolverBudget:
    """Frozen compute and randomness limits shared by stochastic solvers."""

    maximum_candidate_evaluations: int
    seed: int
    population_size: int = 12
    maximum_time_s: float = 10.0

    def __post_init__(self) -> None:
        if self.maximum_candidate_evaluations < 1 or self.population_size < 4 or self.maximum_time_s <= 0:
            raise ValueError("Solver evaluation and population budgets must be positive")


class RequirementsFirstSynthesisSolver(ABC):
    """Strategy contract whose input type cannot contain evaluator evidence."""

    @abstractmethod
    def solve(self, view: SolverBenchmarkView) -> RequirementsSynthesisResult:
        """Synthesize from requirements without a reference train or label."""


class RequirementsCandidateValidator(ABC):
    """Replaceable in-loop candidate-admission strategy."""

    @abstractmethod
    def validate(self, specification: ProblemSpecification, train: GearTrain) -> ValidationCertificate:
        """Return the production-model certificate for a generated candidate."""


class SynthesisGeometryKernel:
    """Small numerical kernel for placement generation and obstacle checks."""

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
        base = Point2D(first.x + along * unit_x, first.y + along * unit_y)
        offset = Point2D(-unit_y * height, unit_x * height)
        first_solution = Point2D(base.x + offset.x, base.y + offset.y)
        return (first_solution,) if height <= 1e-12 else (first_solution, Point2D(base.x - offset.x, base.y - offset.y))

    @classmethod
    def stage_overlaps_obstacle(cls, stage: GearStage, obstacle: tuple[Point2D, ...], clearance: float) -> bool:
        radius = stage.outer_radius_mm() + clearance
        if cls._point_inside(stage.center, obstacle):
            return True
        return any(
            cls._distance_to_segment(stage.center, obstacle[index], obstacle[(index + 1) % len(obstacle)]) < radius - 1e-9
            for index in range(len(obstacle))
        )

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

    @staticmethod
    def _distance_to_segment(point: Point2D, first: Point2D, second: Point2D) -> float:
        dx = second.x - first.x
        dy = second.y - first.y
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            return hypot(point.x - first.x, point.y - first.y)
        projection = max(0.0, min(1.0, ((point.x - first.x) * dx + (point.y - first.y) * dy) / length_squared))
        return hypot(point.x - (first.x + projection * dx), point.y - (first.y + projection * dy))


class ProductionCandidateValidator(RequirementsCandidateValidator):
    """Physical verifier plus an independent full-specification trust boundary."""

    def __init__(
        self,
        geometry: SynthesisGeometryKernel | None = None,
        specification_validator: ProblemSpecificationValidator | None = None,
    ):
        self._geometry = geometry or SynthesisGeometryKernel()
        self._certificate_binder = ValidationCertificateBinder()
        self._specification_validator = specification_validator or ProblemSpecificationValidator((
            PrescribedShaftValidationRule(),
            DesignSpaceValidationRule(),
            ObstacleValidationRule(self._geometry),
        ))

    def validate(self, specification: ProblemSpecification, train: GearTrain) -> ValidationCertificate:
        certificate = ReferenceVerifier.verify_with_cae(specification.problem, train)
        issues = (*certificate.issues, *self._specification_validator.validate(specification, train))
        identity = certificate.model_identity
        certificate = replace(
            certificate,
            valid=not issues,
            issues=issues,
            model_identity=CertificateModelIdentity(
                planar_model=identity.planar_model,
                specification_model=specification.schema_version,
                static_strength_model=identity.static_strength_model,
                strength_qualification_evidence=identity.strength_qualification_evidence,
            ),
        )
        return self._certificate_binder.bind(
            certificate,
            specification,
            train,
            subject_schema=specification.schema_version,
            verifier_identity=certificate.model_identity.planar_model,
        )


class EnumerativeCompoundSynthesizer(RequirementsFirstSynthesisSolver):
    """Complete blind enumerator for the declared three-shaft compound family."""

    def __init__(
        self,
        validator: RequirementsCandidateValidator,
        geometry: SynthesisGeometryKernel | None = None,
        budget: SolverBudget | None = None,
    ):
        self._validator = validator
        self._geometry = geometry or SynthesisGeometryKernel()
        self._budget = budget

    def solve(self, view: SolverBenchmarkView) -> RequirementsSynthesisResult:
        specification = view.specification
        space = specification.design_space
        if space.minimum_stage_count > 3 or space.maximum_stage_count < 3 or space.maximum_compound_members < 2:
            return RequirementsSynthesisResult(None, 0, 0, True, None)
        terminals = {shaft.role: shaft.center for shaft in specification.prescribed_shafts}
        constraints = specification.problem.constraints
        evaluated_parameters = 0
        evaluated_placements = 0
        for module in space.allowed_modules_mm:
            for tooth_tuple in product(range(constraints.min_teeth, constraints.max_teeth + 1), repeat=4):
                evaluated_parameters += 1
                if self._budget is not None and evaluated_parameters > self._budget.maximum_candidate_evaluations:
                    return RequirementsSynthesisResult(
                        None,
                        self._budget.maximum_candidate_evaluations,
                        evaluated_placements,
                        False,
                        None,
                    )
                input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
                ratio = input_teeth / first_compound * second_compound / output_teeth
                if constraints.target_speed_ratio is not None and not isclose(
                    ratio,
                    constraints.target_speed_ratio,
                    rel_tol=constraints.ratio_tolerance,
                    abs_tol=constraints.ratio_tolerance,
                ):
                    continue
                input_distance = module * (input_teeth + first_compound) / 2.0
                output_distance = module * (second_compound + output_teeth) / 2.0
                placements = self._geometry.circle_intersections(
                    terminals["input"], input_distance, terminals["output"], output_distance
                )
                evaluated_placements += len(placements)
                for compound_center in placements:
                    train = self._train(
                        terminals,
                        compound_center,
                        module,
                        tooth_tuple,
                        space.mesh_center_distance_tolerance_mm,
                    )
                    certificate = self._validator.validate(specification, train)
                    if certificate.valid:
                        return RequirementsSynthesisResult(train, evaluated_parameters, evaluated_placements, False, certificate)
        return RequirementsSynthesisResult(None, evaluated_parameters, evaluated_placements, True, None)

    @staticmethod
    def _train(
        terminals: dict[str, Point2D],
        compound_center: Point2D,
        module: float,
        tooth_tuple: tuple[int, int, int, int],
        mesh_tolerance_mm: float,
    ) -> GearTrain:
        input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
        return GearTrain(
            (
                GearStage("input", terminals["input"], (input_teeth,), module, (0,)),
                GearStage("compound", compound_center, (first_compound, second_compound), module, (0, 1)),
                GearStage("output", terminals["output"], (output_teeth,), module, (1,)),
            ),
            (
                MeshEdge("input", 0, "compound", 0, mesh_tolerance_mm),
                MeshEdge("compound", 1, "output", 0, mesh_tolerance_mm),
            ),
        )


class EvolutionaryCompoundSynthesizer(RequirementsFirstSynthesisSolver):
    """Seeded differential-evolution baseline over discrete design decisions."""

    def __init__(
        self,
        validator: RequirementsCandidateValidator,
        budget: SolverBudget,
        geometry: SynthesisGeometryKernel | None = None,
    ):
        self._validator = validator
        self._budget = budget
        self._geometry = geometry or SynthesisGeometryKernel()

    def solve(self, view: SolverBenchmarkView) -> RequirementsSynthesisResult:
        specification = view.specification
        space = specification.design_space
        constraints = specification.problem.constraints
        modules = space.allowed_modules_mm
        terminals = {shaft.role: shaft.center for shaft in specification.prescribed_shafts}
        evaluated: set[tuple[int, int, int, int, int]] = set()
        placements_evaluated = 0
        best_train: GearTrain | None = None
        best_certificate: ValidationCertificate | None = None
        bounds = (
            (0, len(modules) - 1),
            *((constraints.min_teeth, constraints.max_teeth),) * 4,
        )

        def objective(vector: np.ndarray) -> float:
            nonlocal placements_evaluated, best_train, best_certificate
            module_index = int(np.clip(np.rint(vector[0]), 0, len(modules) - 1))
            tooth_tuple = tuple(
                int(np.clip(np.rint(value), constraints.min_teeth, constraints.max_teeth))
                for value in vector[1:]
            )
            key = (module_index, *tooth_tuple)
            if key in evaluated:
                return self._algebraic_penalty(specification, modules[module_index], tooth_tuple, terminals)
            if len(evaluated) >= self._budget.maximum_candidate_evaluations:
                return 1e6
            evaluated.add(key)
            module = modules[module_index]
            penalty = self._algebraic_penalty(specification, module, tooth_tuple, terminals)
            if penalty > 1e-12:
                return penalty
            input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
            placements = self._geometry.circle_intersections(
                terminals["input"],
                module * (input_teeth + first_compound) / 2.0,
                terminals["output"],
                module * (second_compound + output_teeth) / 2.0,
            )
            placements_evaluated += len(placements)
            for center in placements:
                train = EnumerativeCompoundSynthesizer._train(
                    terminals, center, module, tooth_tuple, space.mesh_center_distance_tolerance_mm
                )
                certificate = self._validator.validate(specification, train)
                if certificate.valid:
                    best_train = train
                    best_certificate = certificate
                    return 0.0
            return 1.0

        def stop(_vector: np.ndarray, _convergence: float) -> bool:
            return best_train is not None or len(evaluated) >= self._budget.maximum_candidate_evaluations

        dimensions = len(bounds)
        maximum_iterations = max(1, self._budget.maximum_candidate_evaluations // (self._budget.population_size * dimensions))
        differential_evolution(
            objective,
            bounds,
            seed=self._budget.seed,
            popsize=self._budget.population_size,
            maxiter=maximum_iterations,
            polish=False,
            updating="immediate",
            workers=1,
            callback=stop,
            integrality=np.ones(dimensions, dtype=bool),
            tol=0.0,
            atol=0.0,
        )
        return RequirementsSynthesisResult(
            best_train,
            len(evaluated),
            placements_evaluated,
            False,
            best_certificate,
        )

    @staticmethod
    def _algebraic_penalty(
        specification: ProblemSpecification,
        module: float,
        tooth_tuple: tuple[int, int, int, int],
        terminals: dict[str, Point2D],
    ) -> float:
        constraints = specification.problem.constraints
        input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
        ratio = input_teeth / first_compound * second_compound / output_teeth
        ratio_penalty = 0.0
        if constraints.target_speed_ratio is not None:
            scale = max(abs(constraints.target_speed_ratio), 1e-12)
            ratio_penalty = abs(ratio - constraints.target_speed_ratio) / scale
            if ratio_penalty <= constraints.ratio_tolerance / scale:
                ratio_penalty = 0.0
        first_radius = module * (input_teeth + first_compound) / 2.0
        second_radius = module * (second_compound + output_teeth) / 2.0
        terminal_distance = hypot(
            terminals["output"].x - terminals["input"].x,
            terminals["output"].y - terminals["input"].y,
        )
        triangle_violation = max(
            0.0,
            terminal_distance - first_radius - second_radius,
            abs(first_radius - second_radius) - terminal_distance,
        ) / max(terminal_distance, 1.0)
        return ratio_penalty + triangle_violation


@dataclass(frozen=True)
class CpSatBackendResult:
    candidates: tuple[tuple[int, int, int, int], ...]
    search_complete: bool


class CpSatBackend(ABC):
    """Process-isolated integer-constraint backend contract."""

    @abstractmethod
    def candidates(self, request: dict, timeout_s: float) -> CpSatBackendResult:
        """Return algebraically admissible tooth tuples and proof status."""


class SubprocessCpSatBackend(CpSatBackend):
    """Keep OR-Tools' protobuf runtime isolated from PyTorch's runtime."""

    def __init__(self, worker_path: Path | None = None):
        self._worker_path = worker_path or Path(__file__).resolve().parents[1] / "cp_sat_worker.py"

    def candidates(self, request: dict, timeout_s: float) -> CpSatBackendResult:
        completed = subprocess.run(
            (sys.executable, str(self._worker_path)),
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=timeout_s + 5.0,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"CP-SAT worker failed: {completed.stderr.strip()}")
        payload = json.loads(completed.stdout)
        return CpSatBackendResult(
            tuple(tuple(int(value) for value in candidate) for candidate in payload["candidates"]),
            bool(payload["search_complete"]),
        )


class CpSatCompoundSynthesizer(RequirementsFirstSynthesisSolver):
    """Process-isolated CP-SAT baseline with certificate admission."""

    def __init__(
        self,
        validator: RequirementsCandidateValidator,
        budget: SolverBudget,
        geometry: SynthesisGeometryKernel | None = None,
        backend: CpSatBackend | None = None,
    ):
        self._validator = validator
        self._budget = budget
        self._geometry = geometry or SynthesisGeometryKernel()
        self._backend = backend or SubprocessCpSatBackend()

    def solve(self, view: SolverBenchmarkView) -> RequirementsSynthesisResult:
        specification = view.specification
        space = specification.design_space
        if space.minimum_stage_count > 3 or space.maximum_stage_count < 3 or space.maximum_compound_members < 2:
            return RequirementsSynthesisResult(None, 0, 0, True, None)
        terminals = {shaft.role: shaft.center for shaft in specification.prescribed_shafts}
        terminal_distance = hypot(
            terminals["output"].x - terminals["input"].x,
            terminals["output"].y - terminals["input"].y,
        )
        constraints = specification.problem.constraints
        if constraints.target_speed_ratio is not None and constraints.target_speed_ratio < 0:
            return RequirementsSynthesisResult(None, 0, 0, True, None)
        evaluated = 0
        placements_evaluated = 0
        for module in space.allowed_modules_mm:
            remaining = self._budget.maximum_candidate_evaluations - evaluated
            if remaining <= 0:
                return RequirementsSynthesisResult(None, evaluated, placements_evaluated, False, None)
            backend_result = self._backend.candidates(
                {
                    "minimum_teeth": constraints.min_teeth,
                    "maximum_teeth": constraints.max_teeth,
                    "target_speed_ratio": constraints.target_speed_ratio,
                    "ratio_tolerance": constraints.ratio_tolerance,
                    "module_mm": module,
                    "terminal_distance_mm": terminal_distance,
                    "maximum_candidates": remaining,
                    "maximum_time_s": self._budget.maximum_time_s,
                    "seed": self._budget.seed,
                },
                self._budget.maximum_time_s,
            )
            for tooth_tuple in backend_result.candidates:
                evaluated += 1
                input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
                placements = self._geometry.circle_intersections(
                    terminals["input"],
                    module * (input_teeth + first_compound) / 2.0,
                    terminals["output"],
                    module * (second_compound + output_teeth) / 2.0,
                )
                placements_evaluated += len(placements)
                for center in placements:
                    train = EnumerativeCompoundSynthesizer._train(
                        terminals, center, module, tooth_tuple, space.mesh_center_distance_tolerance_mm
                    )
                    certificate = self._validator.validate(specification, train)
                    if certificate.valid:
                        return RequirementsSynthesisResult(train, evaluated, placements_evaluated, False, certificate)
            if not backend_result.search_complete:
                return RequirementsSynthesisResult(None, evaluated, placements_evaluated, False, None)
        return RequirementsSynthesisResult(None, evaluated, placements_evaluated, True, None)
