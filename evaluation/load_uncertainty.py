"""Uncertainty propagation for the verified linear-elastic CAE response."""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from random import Random
from statistics import mean

import numpy as np
from scipy.stats import qmc


@dataclass(frozen=True)
class UniformRange:
    name: str
    lower: float
    upper: float
    unit: str

    def __post_init__(self) -> None:
        if self.lower >= self.upper:
            raise ValueError("Uncertainty range must have positive width")

    def transform(self, unit_values: np.ndarray) -> np.ndarray:
        return self.lower + unit_values * (self.upper - self.lower)


@dataclass(frozen=True)
class StaticLoadUncertaintyModel:
    """Declared aleatory ranges; material strength remains a fixed sourced datum."""

    torque_nm: UniformRange = UniformRange("input_torque", 1.0, 3.0, "N m")
    face_width_mm: UniformRange = UniformRange("face_width", 8.0, 12.0, "mm")
    efficiency: UniformRange = UniformRange("per_mesh_efficiency", 0.95, 0.98, "1")

    @property
    def dimensions(self) -> tuple[UniformRange, ...]:
        return self.torque_nm, self.face_width_mm, self.efficiency

    def transform(self, unit_samples: np.ndarray) -> np.ndarray:
        if unit_samples.ndim != 2 or unit_samples.shape[1] != len(self.dimensions):
            raise ValueError("Expected an N by 3 unit-hypercube sample")
        return np.column_stack([dimension.transform(unit_samples[:, index]) for index, dimension in enumerate(self.dimensions)])


@dataclass(frozen=True)
class ToothResponseSurface:
    """Exact load scaling for a force-controlled linear plane-stress model."""

    reference_stress_mpa: float
    allowable_stress_mpa: float
    reference_torque_nm: float
    reference_face_width_mm: float
    reference_efficiency: float
    mesh_depth: int

    @classmethod
    def from_report(cls, report: dict, load_case: dict) -> "ToothResponseSurface":
        efficiency = float(load_case["efficiency"])
        cumulative = float(report["cumulative_mesh_efficiency"])
        depth = 0 if cumulative == 1.0 else round(log(cumulative) / log(efficiency))
        if depth < 0 or abs(cumulative - efficiency**depth) > 1e-8:
            raise ValueError("Report efficiency is inconsistent with an integer mesh depth")
        return cls(
            float(report["max_von_mises_mpa"]),
            float(load_case["allowable_stress_mpa"]),
            float(load_case["input_torque_nm"]),
            float(load_case["face_width_mm"]),
            efficiency,
            depth,
        )

    def safety_factor(self, samples: np.ndarray) -> np.ndarray:
        torque, width, efficiency = samples.T
        stress = (
            self.reference_stress_mpa
            * torque
            / self.reference_torque_nm
            * self.reference_face_width_mm
            / width
            * (efficiency / self.reference_efficiency) ** self.mesh_depth
        )
        return self.allowable_stress_mpa / stress


@dataclass(frozen=True)
class LayoutResponseSurface:
    instance_id: str
    teeth: tuple[ToothResponseSurface, ...]

    def minimum_safety_factor(self, samples: np.ndarray) -> np.ndarray:
        return np.min(np.vstack([tooth.safety_factor(samples) for tooth in self.teeth]), axis=0)


@dataclass(frozen=True)
class SobolIndices:
    parameter: str
    first_order: float
    total_order: float


@dataclass(frozen=True)
class LayoutUncertaintyOutcome:
    instance_id: str
    failure_probability: float
    safety_q05: float
    safety_q50: float
    safety_q95: float


@dataclass(frozen=True)
class MaterialUncertaintySummary:
    material_name: str
    layout_count: int
    sample_count: int
    pooled_failure_probability: float
    layout_bootstrap_ci95: tuple[float, float]
    safety_quantiles: dict[str, float]
    sensitivity: tuple[SobolIndices, ...]
    layout_outcomes: tuple[LayoutUncertaintyOutcome, ...]


class DirectCornerValidator:
    """Validate response surfaces against independently persisted direct solves."""

    def maximum_relative_error(self, reference_record: dict, comparison_records: tuple[dict, ...]) -> float:
        surfaces = self._surfaces(reference_record)
        maximum = 0.0
        for record in comparison_records:
            sample = np.array([[
                record["load_case"]["input_torque_nm"],
                record["load_case"]["face_width_mm"],
                record["load_case"]["efficiency"],
            ]])
            for layout in record["layout_outcomes"]:
                predicted = surfaces[layout["instance_id"]].minimum_safety_factor(sample)[0]
                observed = float(layout["minimum_safety_factor"])
                maximum = max(maximum, abs(predicted - observed) / observed)
        return maximum

    @staticmethod
    def _surfaces(record: dict) -> dict[str, LayoutResponseSurface]:
        return {
            layout["instance_id"]: LayoutResponseSurface(
                layout["instance_id"],
                tuple(ToothResponseSurface.from_report(report, record["load_case"]) for report in layout["reports"]),
            )
            for layout in record["layout_outcomes"]
        }


class SobolLoadUncertaintyStudy:
    """Propagate load uncertainty and estimate variance-based sensitivity."""

    def __init__(self, model: StaticLoadUncertaintyModel, seed: int, bootstrap_samples: int = 5_000):
        if bootstrap_samples < 100:
            raise ValueError("At least 100 layout-bootstrap samples are required")
        self._model = model
        self._seed = seed
        self._bootstrap_samples = bootstrap_samples

    def evaluate(self, material_name: str, reference_record: dict, exponent: int) -> MaterialUncertaintySummary:
        if exponent < 4:
            raise ValueError("Sobol exponent must be at least four")
        surfaces = tuple(DirectCornerValidator._surfaces(reference_record).values())
        joint = qmc.Sobol(d=6, scramble=True, seed=self._seed).random_base2(exponent)
        unit_a, unit_b = joint[:, :3], joint[:, 3:]
        samples_a, samples_b = self._model.transform(unit_a), self._model.transform(unit_b)
        layout_values = [surface.minimum_safety_factor(samples_a) for surface in surfaces]
        pooled = np.concatenate(layout_values)
        layout_failure = [float(np.mean(values < 1.0)) for values in layout_values]
        layout_outcomes = tuple(
            LayoutUncertaintyOutcome(
                surface.instance_id,
                failure,
                *map(float, np.quantile(values, [0.05, 0.5, 0.95])),
            )
            for surface, values, failure in zip(surfaces, layout_values, layout_failure)
        )
        sensitivity = self._sensitivity(surfaces, samples_a, samples_b)
        ordered = np.quantile(pooled, [0.025, 0.05, 0.5, 0.95, 0.975])
        return MaterialUncertaintySummary(
            material_name,
            len(surfaces),
            len(samples_a),
            float(np.mean(pooled < 1.0)),
            self._bootstrap_ci(layout_failure),
            dict(zip(("q025", "q05", "q50", "q95", "q975"), map(float, ordered))),
            sensitivity,
            layout_outcomes,
        )

    def _sensitivity(
        self, surfaces: tuple[LayoutResponseSurface, ...], samples_a: np.ndarray, samples_b: np.ndarray
    ) -> tuple[SobolIndices, ...]:
        indices = []
        for index, dimension in enumerate(self._model.dimensions):
            hybrid = samples_a.copy()
            hybrid[:, index] = samples_b[:, index]
            first_by_layout, total_by_layout = [], []
            for surface in surfaces:
                values_a = surface.minimum_safety_factor(samples_a)
                values_b = surface.minimum_safety_factor(samples_b)
                values_hybrid = surface.minimum_safety_factor(hybrid)
                variance = float(np.var(np.concatenate((values_a, values_b)), ddof=1))
                first_by_layout.append(float(np.mean(values_b * (values_hybrid - values_a)) / variance))
                total_by_layout.append(float(0.5 * np.mean((values_a - values_hybrid) ** 2) / variance))
            indices.append(SobolIndices(dimension.name, mean(first_by_layout), mean(total_by_layout)))
        return tuple(indices)

    def _bootstrap_ci(self, values: list[float]) -> tuple[float, float]:
        random = Random(self._seed)
        draws = sorted(mean(random.choice(values) for _ in values) for _ in range(self._bootstrap_samples))
        return draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]
