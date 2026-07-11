"""Stratified in-house CAE screening study for certified benchmark layouts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from benchmark.generator import BenchmarkInstance
from common.design_models import GearTrain, MaterialLoadCase
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class CAEStudyOutcome:
    instance_id: str
    valid: bool
    minimum_safety_factor: float | None
    report_count: int
    reports: tuple[dict, ...] = ()


class StratifiedCAEStudy:
    """Run a declared load case on a reproducible, family-stratified sample."""

    def __init__(self, load_case: MaterialLoadCase, minimum_safety_factor: float):
        self._load_case = load_case
        self._minimum_safety_factor = minimum_safety_factor

    def evaluate(self, instances: list[BenchmarkInstance], sample_size: int) -> list[CAEStudyOutcome]:
        if sample_size < 1:
            raise ValueError("sample_size must be positive")
        selected = self._select(instances, sample_size)
        outcomes = []
        for instance in selected:
            constraints = replace(instance.problem.constraints, min_safety_factor=self._minimum_safety_factor)
            problem = replace(instance.problem, constraints=constraints, load_case=self._load_case)
            certificate = ReferenceVerifier.verify_with_cae(problem, self._solution_train(instance))
            safety = [float(report["safety_factor"]) for report in certificate.cae_reports]
            outcomes.append(
                CAEStudyOutcome(
                    instance.instance_id,
                    certificate.valid,
                    min(safety) if safety else None,
                    len(safety),
                    tuple(certificate.cae_reports),
                )
            )
        return outcomes

    @staticmethod
    def _select(instances: list[BenchmarkInstance], sample_size: int) -> list[BenchmarkInstance]:
        if not instances:
            raise ValueError("instances are required")
        by_family: dict[str, list[BenchmarkInstance]] = {}
        for instance in instances:
            if instance.expected_feasible:
                by_family.setdefault(instance.family, []).append(instance)
        selected: list[BenchmarkInstance] = []
        target_size = min(sample_size, sum(len(items) for items in by_family.values()))
        while len(selected) < target_size:
            progressed = False
            for family in sorted(by_family):
                if by_family[family] and len(selected) < target_size:
                    selected.append(by_family[family].pop(0))
                    progressed = True
            if not progressed:
                break
        return selected

    @staticmethod
    def _solution_train(instance: BenchmarkInstance) -> GearTrain:
        """Screen the actual synthesized path rather than branch-ordering decoys."""
        stages = tuple(stage for stage in instance.reference_train.stages if stage.id in {"input", "compound", "output"})
        meshes = tuple(edge for edge in instance.reference_train.meshes if edge.driver_stage_id in {"input", "compound"} and edge.driven_stage_id in {"compound", "output"})
        return GearTrain(stages, meshes)
