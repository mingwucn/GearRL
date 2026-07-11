"""Stratified in-house CAE screening study for certified benchmark layouts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from benchmark.generator import BenchmarkInstance
from common.design_models import MaterialLoadCase
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class CAEStudyOutcome:
    instance_id: str
    valid: bool
    minimum_safety_factor: float | None
    report_count: int


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
            certificate = ReferenceVerifier.verify_with_cae(problem, instance.reference_train)
            safety = [float(report["safety_factor"]) for report in certificate.cae_reports]
            outcomes.append(CAEStudyOutcome(instance.instance_id, certificate.valid, min(safety) if safety else None, len(safety)))
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
