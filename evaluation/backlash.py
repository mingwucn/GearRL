"""Backlash-aware center-distance expansion study for collinear gear trains."""

from __future__ import annotations

from dataclasses import dataclass, replace

from common.design_models import DesignProblem, GearTrain, Point2D
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class BacklashOutcome:
    transverse_backlash_allowance_mm: float
    center_expansion_per_mesh_mm: float
    valid: bool


class BacklashRobustnessEvaluator:
    """Evaluate uniform positive center-distance expansion along a train path."""

    def evaluate(self, problem: DesignProblem, train: GearTrain, allowances_mm: tuple[float, ...], expansions_mm: tuple[float, ...]) -> list[BacklashOutcome]:
        if not allowances_mm or not expansions_mm:
            raise ValueError("Backlash allowances and center expansions are required")
        outcomes = []
        for allowance in allowances_mm:
            if allowance < 0:
                raise ValueError("Backlash allowance must be non-negative")
            constraints = replace(problem.constraints, transverse_backlash_allowance_mm=allowance)
            declared_problem = replace(problem, constraints=constraints)
            for expansion in expansions_mm:
                if expansion < 0:
                    raise ValueError("Backlash study permits only positive center-distance expansion")
                stages = tuple(replace(stage, center=Point2D(stage.center.x + index * expansion, stage.center.y)) for index, stage in enumerate(train.stages))
                certificate = ReferenceVerifier.verify(declared_problem, GearTrain(stages, train.meshes))
                outcomes.append(BacklashOutcome(allowance, expansion, certificate.valid))
        return outcomes
