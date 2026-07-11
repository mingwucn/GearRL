"""Paired evidence that static-strength requirements alter blind synthesis."""

from __future__ import annotations

from dataclasses import dataclass, replace

from benchmark.specification import SolverBenchmarkView
from common.design_models import MaterialLoadCase
from synthesis.requirements_solver import RequirementsCandidateValidator, RequirementsFirstSynthesisSolver


@dataclass(frozen=True)
class StrengthCouplingRequirements:
    load_case: MaterialLoadCase
    minimum_safety_factor: float

    def __post_init__(self) -> None:
        if self.minimum_safety_factor <= 0:
            raise ValueError("Minimum safety factor must be positive")

    def apply(self, view: SolverBenchmarkView) -> SolverBenchmarkView:
        problem = replace(
            view.specification.problem,
            constraints=replace(
                view.specification.problem.constraints,
                min_safety_factor=self.minimum_safety_factor,
            ),
            load_case=self.load_case,
        )
        return replace(view, specification=replace(view.specification, problem=problem))


@dataclass(frozen=True)
class StrengthCoupledOutcome:
    instance_id: str
    classification: str
    baseline_train: dict
    baseline_parameter_tuples_evaluated: int
    baseline_minimum_safety_factor: float
    baseline_admissible_under_strength: bool
    strength_train: dict | None
    strength_parameter_tuples_evaluated: int
    strength_search_complete: bool
    strength_minimum_safety_factor: float | None
    design_changed: bool
    baseline_strength_certificate: dict
    strength_certificate: dict | None


class StrengthCoupledSynthesisStudy:
    """Compare geometry-only and strength-admitted synthesis on identical views."""

    def __init__(
        self,
        solver: RequirementsFirstSynthesisSolver,
        validator: RequirementsCandidateValidator,
        requirements: StrengthCouplingRequirements,
    ):
        self._solver = solver
        self._validator = validator
        self._requirements = requirements

    def evaluate(self, views: tuple[SolverBenchmarkView, ...]) -> tuple[StrengthCoupledOutcome, ...]:
        outcomes = []
        for view in views:
            baseline = self._solver.solve(view)
            if baseline.train is None:
                raise RuntimeError(f"Predeclared coupling case lacks a baseline design: {view.instance_id}")
            strength_view = self._requirements.apply(view)
            baseline_certificate = self._validator.validate(strength_view.specification, baseline.train)
            baseline_safety = self._minimum_safety(baseline_certificate.cae_reports)
            strength = self._solver.solve(strength_view)
            if strength.train is None and not strength.search_complete:
                raise RuntimeError(f"Strength rejection is not a complete proof: {view.instance_id}")
            strength_safety = self._minimum_safety(strength.certificate.cae_reports) if strength.certificate else None
            changed = strength.train is not None and strength.train.to_json() != baseline.train.to_json()
            classification = "rejected" if strength.train is None else "redesigned" if changed else "retained"
            outcomes.append(
                StrengthCoupledOutcome(
                    view.instance_id,
                    classification,
                    baseline.train.to_json(),
                    baseline.parameter_tuples_evaluated,
                    baseline_safety,
                    baseline_certificate.valid,
                    strength.train.to_json() if strength.train else None,
                    strength.parameter_tuples_evaluated,
                    strength.search_complete,
                    strength_safety,
                    changed,
                    baseline_certificate.to_json(),
                    strength.certificate.to_json() if strength.certificate else None,
                )
            )
        return tuple(outcomes)

    @staticmethod
    def _minimum_safety(reports: list[dict]) -> float:
        if not reports:
            raise RuntimeError("Strength coupling requires CAE reports")
        return min(float(report["safety_factor"]) for report in reports)
