"""Independent geometric-tolerance analysis for certified gear layouts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from common.design_models import GearStage, GearTrain, Point2D
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class ToleranceOutcome:
    offset_mm: float
    valid: bool
    minimum_clearance_mm: float | None


class GeometricToleranceEvaluator:
    """Evaluate deterministic shaft-position perturbations against the reference verifier."""

    def evaluate(self, problem, train: GearTrain, offsets_mm: tuple[float, ...]) -> list[ToleranceOutcome]:
        if not offsets_mm:
            raise ValueError("At least one tolerance offset is required")
        outcomes: list[ToleranceOutcome] = []
        for offset in offsets_mm:
            perturbed = self._perturb(train, offset)
            certificate = ReferenceVerifier.verify(problem, perturbed)
            outcomes.append(ToleranceOutcome(offset, certificate.valid, certificate.minimum_clearance_mm))
        return outcomes

    @staticmethod
    def _perturb(train: GearTrain, offset_mm: float) -> GearTrain:
        stages = []
        for index, stage in enumerate(train.stages):
            if index == 0:
                stages.append(stage)
                continue
            stages.append(replace(stage, center=Point2D(stage.center.x, stage.center.y + offset_mm)))
        return GearTrain(tuple(stages), train.meshes)
