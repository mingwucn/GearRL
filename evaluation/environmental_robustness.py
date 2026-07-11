"""Declared housing-clearance and static-load robustness analyses."""

from __future__ import annotations

from dataclasses import dataclass, replace

from benchmark.generator import BenchmarkInstance
from common.design_models import GearTrain, MaterialLoadCase
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class HousingRobustnessOutcome:
    instance_id: str
    clearance_erosion_mm: float
    valid: bool
    minimum_clearance_mm: float | None


@dataclass(frozen=True)
class LoadRobustnessOutcome:
    instance_id: str
    load_multiplier: float
    valid: bool
    minimum_safety_factor: float | None
    issue_codes: tuple[str, ...]


class EnvironmentalRobustnessEvaluator:
    """Reverify selected trains under declared housing and load variations."""

    def evaluate_housing(self, instance: BenchmarkInstance, train: GearTrain, erosions_mm: tuple[float, ...]) -> list[HousingRobustnessOutcome]:
        outcomes = []
        for erosion in erosions_mm:
            if erosion < 0:
                raise ValueError("Housing clearance erosion must be non-negative")
            constraints = replace(instance.problem.constraints, boundary_clearance=instance.problem.constraints.boundary_clearance + erosion)
            certificate = ReferenceVerifier.verify(replace(instance.problem, constraints=constraints), train)
            outcomes.append(HousingRobustnessOutcome(instance.instance_id, erosion, certificate.valid, certificate.minimum_clearance_mm))
        return outcomes

    def evaluate_load(self, instance: BenchmarkInstance, train: GearTrain, base_load: MaterialLoadCase, multipliers: tuple[float, ...], minimum_safety_factor: float) -> list[LoadRobustnessOutcome]:
        outcomes = []
        for multiplier in multipliers:
            if multiplier <= 0:
                raise ValueError("Load multiplier must be positive")
            load = replace(base_load, input_torque_nm=base_load.input_torque_nm * multiplier)
            constraints = replace(instance.problem.constraints, min_safety_factor=minimum_safety_factor)
            certificate = ReferenceVerifier.verify_with_cae(replace(instance.problem, constraints=constraints, load_case=load), train)
            safety = [float(report["safety_factor"]) for report in certificate.cae_reports]
            outcomes.append(LoadRobustnessOutcome(
                instance.instance_id,
                multiplier,
                certificate.valid,
                min(safety) if safety else None,
                tuple(sorted({issue.code for issue in certificate.issues})),
            ))
        return outcomes
