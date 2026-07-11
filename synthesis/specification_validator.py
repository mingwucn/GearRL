"""Independent admission rules for the complete solver-visible specification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from math import isclose

from benchmark.specification import ProblemSpecification
from common.design_models import GearTrain, ValidationIssue


class SpecificationValidationRule(ABC):
    """One independently testable solver-visible admission rule."""

    @abstractmethod
    def evaluate(self, specification: ProblemSpecification, train: GearTrain) -> tuple[ValidationIssue, ...]:
        """Return every issue found by this rule."""


class PrescribedShaftValidationRule(SpecificationValidationRule):
    """Bind prescribed input/output roles to canonical problem stage IDs."""

    POSITION_TOLERANCE_MM = 1e-9

    def evaluate(self, specification: ProblemSpecification, train: GearTrain) -> tuple[ValidationIssue, ...]:
        stages = train.stage_map()
        role_ids = {
            "input": specification.problem.input_stage_id,
            "output": specification.problem.output_stage_id,
        }
        issues = []
        for shaft in specification.prescribed_shafts:
            stage_id = role_ids[shaft.role]
            stage = stages.get(stage_id)
            if stage is None:
                issues.append(ValidationIssue("prescribed_shaft_missing", f"Prescribed {shaft.role} stage {stage_id} is missing"))
                continue
            if not (
                isclose(stage.center.x, shaft.center.x, rel_tol=0.0, abs_tol=self.POSITION_TOLERANCE_MM)
                and isclose(stage.center.y, shaft.center.y, rel_tol=0.0, abs_tol=self.POSITION_TOLERANCE_MM)
            ):
                issues.append(ValidationIssue("prescribed_shaft_position", f"Stage {stage_id} does not match the prescribed {shaft.role} center"))
        return tuple(issues)


class DesignSpaceValidationRule(SpecificationValidationRule):
    """Enforce every bounded decision declared by ``DesignSpace``."""

    MODULE_TOLERANCE_MM = 1e-12

    def evaluate(self, specification: ProblemSpecification, train: GearTrain) -> tuple[ValidationIssue, ...]:
        space = specification.design_space
        issues = []
        stage_count = len(train.stages)
        if not space.minimum_stage_count <= stage_count <= space.maximum_stage_count:
            issues.append(ValidationIssue("design_space_stage_count", f"Stage count {stage_count} is outside the declared design space"))
        for stage in train.stages:
            if not any(isclose(stage.module_mm, allowed, rel_tol=0.0, abs_tol=self.MODULE_TOLERANCE_MM) for allowed in space.allowed_modules_mm):
                issues.append(ValidationIssue("design_space_module", f"Stage {stage.id} uses undeclared module {stage.module_mm:g} mm"))
            if len(stage.teeth) > space.maximum_compound_members:
                issues.append(ValidationIssue("design_space_compound_members", f"Stage {stage.id} exceeds the compound-member limit"))
            layers = tuple(stage.layer(member) for member in range(len(stage.teeth)))
            if any(layer < 0 or layer >= space.axial_layer_count for layer in layers):
                issues.append(ValidationIssue("design_space_axial_layer", f"Stage {stage.id} uses an undeclared axial layer"))
        return tuple(issues)


class ObstacleValidationRule(SpecificationValidationRule):
    """Reject stages whose outside radius intersects a prescribed obstacle."""

    def __init__(self, geometry) -> None:
        self._geometry = geometry

    def evaluate(self, specification: ProblemSpecification, train: GearTrain) -> tuple[ValidationIssue, ...]:
        clearance = specification.problem.constraints.boundary_clearance
        if any(
            self._geometry.stage_overlaps_obstacle(stage, obstacle, clearance)
            for stage in train.stages
            for obstacle in specification.obstacles
        ):
            return (ValidationIssue("obstacle_interference", "A generated stage intersects a prescribed obstacle"),)
        return ()


class ProblemSpecificationValidator:
    """Composite trust boundary for all requirements visible to a solver."""

    def __init__(self, rules: tuple[SpecificationValidationRule, ...]) -> None:
        if not rules:
            raise ValueError("A problem specification validator requires at least one rule")
        self._rules = rules

    def validate(self, specification: ProblemSpecification, train: GearTrain) -> tuple[ValidationIssue, ...]:
        return tuple(issue for rule in self._rules for issue in rule.evaluate(specification, train))
