"""Predeclared statistical contracts for confirmatory digital assembly evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from benchmark.generator import BenchmarkInstance


@dataclass(frozen=True)
class AssemblyFactorCell:
    shaft_location_tolerance_mm: float
    housing_clearance_erosion_mm: float
    center_distance_backlash_increment_mm: float


@dataclass(frozen=True)
class InteractionHypothesis:
    hypothesis_id: str
    low_shaft_mm: float
    high_shaft_mm: float
    low_backlash_mm: float
    high_backlash_mm: float
    housing_erosion_mm: float
    maximum_interaction: float


@dataclass(frozen=True)
class HousingEquivalenceHypothesis:
    hypothesis_id: str
    reference_erosion_mm: float
    comparison_erosion_mm: float
    equivalence_margin: float


@dataclass(frozen=True)
class ConfirmatoryAssemblyProtocol:
    study_id: str
    population_id: str
    partition: str
    expected_layout_count: int
    random_seed: int
    scramble_replicates: int
    draws_per_replicate: int
    familywise_alpha: float
    shaft_location_tolerances_mm: tuple[float, ...]
    housing_clearance_erosions_mm: tuple[float, ...]
    center_distance_backlash_increments_mm: tuple[float, ...]
    interaction: InteractionHypothesis
    housing_equivalence: HousingEquivalenceHypothesis

    def __post_init__(self) -> None:
        if self.partition != "test":
            raise ValueError("Confirmatory assembly evidence must use the held-out test partition")
        if self.expected_layout_count < 1 or self.scramble_replicates < 4:
            raise ValueError("Confirmatory layout and replicate counts are insufficient")
        if self.draws_per_replicate < 2 or self.draws_per_replicate & (self.draws_per_replicate - 1):
            raise ValueError("Scrambled Sobol draws per replicate must be a power of two")
        if not 0 < self.familywise_alpha < 0.5:
            raise ValueError("Familywise alpha must be between zero and one half")
        factors = (
            self.shaft_location_tolerances_mm,
            self.housing_clearance_erosions_mm,
            self.center_distance_backlash_increments_mm,
        )
        if any(not values or len(values) != len(set(values)) or any(value < 0 for value in values) for values in factors):
            raise ValueError("Confirmatory factors must be unique and non-negative")
        self._validate_hypotheses()

    @property
    def cells(self) -> tuple[AssemblyFactorCell, ...]:
        return tuple(
            AssemblyFactorCell(shaft, housing, backlash)
            for shaft in self.shaft_location_tolerances_mm
            for housing in self.housing_clearance_erosions_mm
            for backlash in self.center_distance_backlash_increments_mm
        )

    @property
    def declared_draw_count(self) -> int:
        return self.expected_layout_count * len(self.cells) * self.scramble_replicates * self.draws_per_replicate

    def _validate_hypotheses(self) -> None:
        interaction = self.interaction
        for value in (interaction.low_shaft_mm, interaction.high_shaft_mm):
            if value not in self.shaft_location_tolerances_mm:
                raise ValueError("Interaction shaft cell is absent from the factor grid")
        for value in (interaction.low_backlash_mm, interaction.high_backlash_mm):
            if value not in self.center_distance_backlash_increments_mm:
                raise ValueError("Interaction backlash cell is absent from the factor grid")
        if interaction.housing_erosion_mm not in self.housing_clearance_erosions_mm:
            raise ValueError("Interaction housing cell is absent from the factor grid")
        if interaction.maximum_interaction >= 0:
            raise ValueError("The directional interaction threshold must be negative")
        equivalence = self.housing_equivalence
        if equivalence.reference_erosion_mm not in self.housing_clearance_erosions_mm or equivalence.comparison_erosion_mm not in self.housing_clearance_erosions_mm:
            raise ValueError("Housing-equivalence cells are absent from the factor grid")
        if equivalence.equivalence_margin <= 0:
            raise ValueError("Housing-equivalence margin must be positive")


class ConfirmatoryAssemblyProtocolLoader:
    """Load the complete preregistered inferential contract without overrides."""

    def load(self, path: Path) -> ConfirmatoryAssemblyProtocol:
        payload = json.loads(path.read_text())
        if payload.get("schema_version") != "assembly-confirmatory-protocol-v2":
            raise ValueError("Unsupported confirmatory assembly protocol schema")
        population = payload["population"]
        computation = payload["computation"]
        factors = payload["factors"]
        inference = payload["inference"]
        interaction = inference["primary_interaction"]
        equivalence = inference["primary_housing_equivalence"]
        return ConfirmatoryAssemblyProtocol(
            payload["study_id"],
            population["population_id"],
            population["partition"],
            int(population["expected_feasible_layout_count"]),
            int(computation["random_seed"]),
            int(computation["scramble_replicates"]),
            int(computation["draws_per_replicate"]),
            float(inference["familywise_alpha"]),
            tuple(map(float, factors["shaft_location_tolerances_mm"])),
            tuple(map(float, factors["housing_clearance_erosions_mm"])),
            tuple(map(float, factors["center_distance_backlash_increments_mm"])),
            InteractionHypothesis(
                interaction["hypothesis_id"],
                float(interaction["low_shaft_mm"]),
                float(interaction["high_shaft_mm"]),
                float(interaction["low_backlash_mm"]),
                float(interaction["high_backlash_mm"]),
                float(interaction["housing_erosion_mm"]),
                float(interaction["maximum_interaction"]),
            ),
            HousingEquivalenceHypothesis(
                equivalence["hypothesis_id"],
                float(equivalence["reference_erosion_mm"]),
                float(equivalence["comparison_erosion_mm"]),
                float(equivalence["equivalence_margin"]),
            ),
        )


class HeldOutFeasibleLayoutCensus:
    """Select the complete declared feasible test-partition population."""

    def select(self, instances: list[BenchmarkInstance], protocol: ConfirmatoryAssemblyProtocol) -> tuple[BenchmarkInstance, ...]:
        selected = tuple(
            instance
            for instance in instances
            if instance.partition == protocol.partition and instance.expected_feasible
        )
        if len(selected) != protocol.expected_layout_count:
            raise ValueError(
                f"Held-out feasible population mismatch: expected {protocol.expected_layout_count}, found {len(selected)}"
            )
        if len({instance.instance_id for instance in selected}) != len(selected):
            raise ValueError("Held-out population contains duplicate layout identifiers")
        return selected
