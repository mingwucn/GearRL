"""Blind requirements-first synthesis strategies and injected validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import product
from math import hypot, isclose, sqrt

from benchmark.specification import ProblemSpecification, SolverBenchmarkView
from common.design_models import GearStage, GearTrain, MeshEdge, Point2D, ValidationCertificate, ValidationIssue
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class RequirementsSynthesisResult:
    """Blind solver outcome with search accounting but no ground-truth fields."""

    train: GearTrain | None
    parameter_tuples_evaluated: int
    placements_evaluated: int
    search_complete: bool
    certificate: ValidationCertificate | None


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
    """Production v2 verifier plus requirements-only obstacle admission."""

    def __init__(self, geometry: SynthesisGeometryKernel | None = None):
        self._geometry = geometry or SynthesisGeometryKernel()

    def validate(self, specification: ProblemSpecification, train: GearTrain) -> ValidationCertificate:
        certificate = ReferenceVerifier.verify_with_cae(specification.problem, train)
        if certificate.valid and any(
            self._geometry.stage_overlaps_obstacle(
                stage,
                obstacle,
                specification.problem.constraints.boundary_clearance,
            )
            for stage in train.stages
            for obstacle in specification.obstacles
        ):
            certificate.valid = False
            certificate.issues.append(ValidationIssue("obstacle_interference", "A generated stage intersects a prescribed obstacle"))
        return certificate


class EnumerativeCompoundSynthesizer(RequirementsFirstSynthesisSolver):
    """Complete blind enumerator for the declared three-shaft compound family."""

    def __init__(
        self,
        validator: RequirementsCandidateValidator,
        geometry: SynthesisGeometryKernel | None = None,
    ):
        self._validator = validator
        self._geometry = geometry or SynthesisGeometryKernel()

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
                    train = self._train(terminals, compound_center, module, tooth_tuple)
                    certificate = self._validator.validate(specification, train)
                    if certificate.valid:
                        return RequirementsSynthesisResult(train, evaluated_parameters, evaluated_placements, False, certificate)
        return RequirementsSynthesisResult(None, evaluated_parameters, evaluated_placements, True, None)

    @staticmethod
    def _train(
        terminals: dict[str, Point2D], compound_center: Point2D, module: float, tooth_tuple: tuple[int, int, int, int]
    ) -> GearTrain:
        input_teeth, first_compound, second_compound, output_teeth = tooth_tuple
        return GearTrain(
            (
                GearStage("input", terminals["input"], (input_teeth,), module, (0,)),
                GearStage("compound", compound_center, (first_compound, second_compound), module, (0, 1)),
                GearStage("output", terminals["output"], (output_teeth,), module, (1,)),
            ),
            (MeshEdge("input", 0, "compound", 0), MeshEdge("compound", 1, "output", 0)),
        )
