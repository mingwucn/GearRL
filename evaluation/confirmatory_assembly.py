"""Predeclared statistical contracts for confirmatory digital assembly evidence."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict, replace
import gzip
from hashlib import sha256
import json
from math import log2, sqrt
from pathlib import Path
import subprocess

from collections import Counter
import numpy as np
from scipy.stats import qmc, t

from benchmark.generator import BenchmarkInstance
from benchmark.loader import FrozenBenchmarkLoader
from evaluation.assembly_robustness import AssemblyDrawOutcome, AssemblyRobustnessEvaluator, AssemblyScenario, AssemblyScenarioIdentity


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


class ScrambledSobolAssemblySampler:
    """Generate independent randomized-QMC replicates with common factor draws."""

    def sample(self, seed: int, draws: int, movable_stage_count: int) -> np.ndarray:
        dimensions = movable_stage_count * 2
        values = qmc.Sobol(dimensions, scramble=True, seed=seed).random_base2(int(log2(draws)))
        return (2.0 * values - 1.0).reshape(draws, movable_stage_count, 2)


class ConfirmatoryScenarioFactory:
    def __init__(self) -> None:
        self._identity = AssemblyScenarioIdentity()

    def create(self, protocol: ConfirmatoryAssemblyProtocol) -> tuple[AssemblyScenario, ...]:
        scenarios = tuple(
            AssemblyScenario(
                self._identity.create(
                    cell.shaft_location_tolerance_mm,
                    cell.housing_clearance_erosion_mm,
                    cell.center_distance_backlash_increment_mm,
                ),
                cell.shaft_location_tolerance_mm,
                cell.housing_clearance_erosion_mm,
                cell.center_distance_backlash_increment_mm,
            )
            for cell in protocol.cells
        )
        if len({scenario.scenario_id for scenario in scenarios}) != len(scenarios):
            raise ValueError("Confirmatory scenario identifiers must be unique")
        return scenarios


class ReplicateConfidenceInterval:
    """Student interval over independent randomized-QMC replicate estimates."""

    def calculate(self, values: np.ndarray, alpha: float) -> tuple[float, float]:
        if values.ndim != 1 or len(values) < 2:
            raise ValueError("Replicate confidence intervals require at least two estimates")
        center = float(values.mean())
        standard_error = float(values.std(ddof=1) / sqrt(len(values)))
        radius = float(t.ppf(1.0 - alpha / 2.0, len(values) - 1) * standard_error)
        return center - radius, center + radius


class ConfirmatoryAssemblyAnalyzer:
    """Apply only the contrasts and familywise rules frozen in the protocol."""

    def __init__(self) -> None:
        self._interval = ReplicateConfidenceInterval()

    @staticmethod
    def _key(shaft: float, housing: float, backlash: float) -> tuple[float, float, float]:
        return shaft, housing, backlash

    def analyze(self, protocol: ConfirmatoryAssemblyProtocol, replicate_means: dict[tuple[float, float, float], np.ndarray]) -> dict:
        hypothesis_alpha = protocol.familywise_alpha / 2.0
        interaction = protocol.interaction
        low_low = replicate_means[self._key(interaction.low_shaft_mm, interaction.housing_erosion_mm, interaction.low_backlash_mm)]
        low_high = replicate_means[self._key(interaction.low_shaft_mm, interaction.housing_erosion_mm, interaction.high_backlash_mm)]
        high_low = replicate_means[self._key(interaction.high_shaft_mm, interaction.housing_erosion_mm, interaction.low_backlash_mm)]
        high_high = replicate_means[self._key(interaction.high_shaft_mm, interaction.housing_erosion_mm, interaction.high_backlash_mm)]
        interaction_values = (high_high - high_low) - (low_high - low_low)
        interaction_interval = self._interval.calculate(interaction_values, hypothesis_alpha)

        equivalence = protocol.housing_equivalence
        equivalence_cells = []
        equivalence_alpha = hypothesis_alpha / (
            len(protocol.shaft_location_tolerances_mm) * len(protocol.center_distance_backlash_increments_mm)
        )
        for shaft in protocol.shaft_location_tolerances_mm:
            for backlash in protocol.center_distance_backlash_increments_mm:
                difference = (
                    replicate_means[self._key(shaft, equivalence.comparison_erosion_mm, backlash)]
                    - replicate_means[self._key(shaft, equivalence.reference_erosion_mm, backlash)]
                )
                interval = self._interval.calculate(difference, equivalence_alpha)
                equivalence_cells.append({
                    "shaft_location_tolerance_mm": shaft,
                    "center_distance_backlash_increment_mm": backlash,
                    "mean_difference": float(difference.mean()),
                    "simultaneous_confidence_interval": list(interval),
                    "within_margin": interval[0] > -equivalence.equivalence_margin and interval[1] < equivalence.equivalence_margin,
                })
        return {
            "familywise_alpha": protocol.familywise_alpha,
            "interaction": {
                "hypothesis_id": interaction.hypothesis_id,
                "estimate": float(interaction_values.mean()),
                "multiplicity_adjusted_confidence_interval": list(interaction_interval),
                "maximum_interaction": interaction.maximum_interaction,
                "supported": interaction_interval[1] < interaction.maximum_interaction,
            },
            "housing_equivalence": {
                "hypothesis_id": equivalence.hypothesis_id,
                "equivalence_margin": equivalence.equivalence_margin,
                "cells": equivalence_cells,
                "supported": all(cell["within_margin"] for cell in equivalence_cells),
            },
        }


class ConfirmatoryAssemblyAccumulator:
    """Bounded-memory aggregate for cell, replicate, and layout outcomes."""

    def __init__(self, scenarios: tuple[AssemblyScenario, ...], protocol: ConfirmatoryAssemblyProtocol) -> None:
        shape = (protocol.scramble_replicates, protocol.expected_layout_count)
        self.valid_counts = {scenario.scenario_id: np.zeros(shape, dtype=np.int32) for scenario in scenarios}
        self.failure_counts = {scenario.scenario_id: Counter() for scenario in scenarios}

    def add(self, layout_index: int, replicate_index: int, outcome: AssemblyDrawOutcome) -> None:
        self.valid_counts[outcome.scenario_id][replicate_index, layout_index] += int(outcome.valid)
        self.failure_counts[outcome.scenario_id].update(set(outcome.failure_codes))


class ConfirmatoryAssemblySummaryBuilder:
    def __init__(self) -> None:
        self._interval = ReplicateConfidenceInterval()
        self._analyzer = ConfirmatoryAssemblyAnalyzer()

    def build(
        self,
        protocol: ConfirmatoryAssemblyProtocol,
        dataset_id: str,
        dataset_hash: str,
        selected: tuple[BenchmarkInstance, ...],
        scenarios: tuple[AssemblyScenario, ...],
        accumulator: ConfirmatoryAssemblyAccumulator,
    ) -> dict:
        scenario_summaries = []
        replicate_means = {}
        for scenario in scenarios:
            rates = accumulator.valid_counts[scenario.scenario_id] / protocol.draws_per_replicate
            corpus_replicates = rates.mean(axis=1)
            key = (
                scenario.shaft_location_tolerance_mm,
                scenario.housing_clearance_erosion_mm,
                scenario.transverse_backlash_allowance_mm,
            )
            replicate_means[key] = corpus_replicates
            scenario_summaries.append({
                "scenario_id": scenario.scenario_id,
                "shaft_location_tolerance_mm": scenario.shaft_location_tolerance_mm,
                "housing_clearance_erosion_mm": scenario.housing_clearance_erosion_mm,
                "center_distance_backlash_increment_mm": scenario.transverse_backlash_allowance_mm,
                "modeled_valid_probability": float(corpus_replicates.mean()),
                "randomized_qmc_95_interval": list(self._interval.calculate(corpus_replicates, 0.05)),
                "replicate_estimates": corpus_replicates.tolist(),
                "minimum_layout_probability": float(rates.mean(axis=0).min()),
                "maximum_layout_probability": float(rates.mean(axis=0).max()),
                "failure_code_counts": dict(sorted(accumulator.failure_counts[scenario.scenario_id].items())),
            })
        return {
            "schema_version": "assembly-confirmatory-summary-v3",
            "study_id": protocol.study_id,
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "population_id": protocol.population_id,
            "layout_ids": [instance.instance_id for instance in selected],
            "family_counts": dict(sorted(Counter(instance.family for instance in selected).items())),
            "protocol": asdict(protocol),
            "layout_count": len(selected),
            "scenario_count": len(scenarios),
            "draw_count": protocol.declared_draw_count,
            "scope": "conditional finite-population digital acceptance; not manufacturing yield or physical validation",
            "scenarios": scenario_summaries,
            "primary_inference": self._analyzer.analyze(protocol, replicate_means),
        }


class ConfirmatoryAssemblyStudy:
    """Stream the preregistered held-out census study to deterministic gzip."""

    def __init__(self) -> None:
        self._census = HeldOutFeasibleLayoutCensus()
        self._scenarios = ConfirmatoryScenarioFactory()
        self._sampler = ScrambledSobolAssemblySampler()
        self._evaluator = AssemblyRobustnessEvaluator()
        self._summary = ConfirmatoryAssemblySummaryBuilder()

    def run(self, dataset: Path, protocol: ConfirmatoryAssemblyProtocol, protocol_source: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Confirmatory assembly destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset)
        selected = self._census.select(instances, protocol)
        scenarios = self._scenarios.create(protocol)
        accumulator = ConfirmatoryAssemblyAccumulator(scenarios, protocol)
        raw_path = destination / "draws.jsonl.gz"
        with raw_path.open("wb") as target:
            with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
                for layout_index, instance in enumerate(selected):
                    movable_count = sum(stage.id != instance.problem.input_stage_id for stage in instance.reference_train.stages)
                    for replicate_index in range(protocol.scramble_replicates):
                        seed = protocol.random_seed + layout_index * protocol.scramble_replicates + replicate_index
                        errors = self._sampler.sample(seed, protocol.draws_per_replicate, movable_count)
                        for scenario in scenarios:
                            for outcome in self._evaluator.evaluate(instance.problem, instance.reference_train, scenario, errors):
                                bound = replace(outcome, layout_id=instance.instance_id)
                                accumulator.add(layout_index, replicate_index, bound)
                                record = {**asdict(bound), "replicate_index": replicate_index}
                                compressed.write(json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n")
        summary = self._summary.build(protocol, dataset_id, dataset_hash, selected, scenarios, accumulator)
        summary_bytes = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
        (destination / "summary.json").write_bytes(summary_bytes)
        commit = subprocess.run(("git", "rev-parse", "HEAD"), text=True, capture_output=True, check=True).stdout.strip()
        manifest = {
            "schema_version": "assembly-confirmatory-artifact-v3",
            "study_id": protocol.study_id,
            "model_version": "certified-planar-v3+assembly-confirmatory-v3",
            "source_commit": commit,
            "source_index": str(dataset / "index.json"),
            "source_index_sha256": sha256((dataset / "index.json").read_bytes()).hexdigest(),
            "protocol_source": str(protocol_source),
            "protocol_source_sha256": sha256(protocol_source.read_bytes()).hexdigest(),
            "summary_sha256": sha256(summary_bytes).hexdigest(),
            "draws_sha256": sha256(raw_path.read_bytes()).hexdigest(),
            "draw_count": protocol.declared_draw_count,
        }
        manifest_path = destination / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest_path


class ConfirmatoryAssemblyEvidenceVerifier:
    """Reconstruct all v3 statistics from the ordered raw evidence stream."""

    def __init__(self) -> None:
        self._census = HeldOutFeasibleLayoutCensus()
        self._scenarios = ConfirmatoryScenarioFactory()
        self._summary = ConfirmatoryAssemblySummaryBuilder()

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        summary_bytes = (destination / "summary.json").read_bytes()
        raw_path = destination / "draws.jsonl.gz"
        if sha256(summary_bytes).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Confirmatory assembly summary hash mismatch")
        if sha256(raw_path.read_bytes()).hexdigest() != manifest["draws_sha256"]:
            raise ValueError("Confirmatory assembly raw-draw hash mismatch")
        protocol_path = Path(manifest["protocol_source"])
        if sha256(protocol_path.read_bytes()).hexdigest() != manifest["protocol_source_sha256"]:
            raise ValueError("Confirmatory assembly protocol hash mismatch")
        index_path = Path(manifest["source_index"])
        if sha256(index_path.read_bytes()).hexdigest() != manifest["source_index_sha256"]:
            raise ValueError("Confirmatory assembly source-index hash mismatch")
        protocol = ConfirmatoryAssemblyProtocolLoader().load(protocol_path)
        dataset = index_path.parent
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset)
        selected = self._census.select(instances, protocol)
        scenarios = self._scenarios.create(protocol)
        accumulator = ConfirmatoryAssemblyAccumulator(scenarios, protocol)
        count = 0
        with gzip.open(raw_path, "rt") as source:
            for layout_index, instance in enumerate(selected):
                for replicate_index in range(protocol.scramble_replicates):
                    for scenario in scenarios:
                        for draw_index in range(protocol.draws_per_replicate):
                            line = source.readline()
                            if not line:
                                raise ValueError("Confirmatory assembly raw evidence ended early")
                            count += 1
                            record = json.loads(line)
                            if (
                                record.get("layout_id") != instance.instance_id
                                or record.get("replicate_index") != replicate_index
                                or record.get("scenario_id") != scenario.scenario_id
                                or record.get("draw_index") != draw_index
                            ):
                                raise ValueError("Confirmatory assembly raw key/order mismatch")
                            outcome = AssemblyDrawOutcome(
                                record["layout_id"],
                                record["scenario_id"],
                                record["draw_index"],
                                bool(record["valid"]),
                                tuple(record["failure_codes"]),
                            )
                            accumulator.add(layout_index, replicate_index, outcome)
            if source.readline():
                raise ValueError("Confirmatory assembly raw evidence has extra draws")
        if count != protocol.declared_draw_count or manifest["draw_count"] != count:
            raise ValueError("Confirmatory assembly draw cardinality mismatch")
        reconstructed = json.loads(json.dumps(self._summary.build(protocol, dataset_id, dataset_hash, selected, scenarios, accumulator)))
        recorded = json.loads(summary_bytes)
        if reconstructed != recorded:
            raise ValueError("Confirmatory assembly semantic summary mismatch")
        return manifest
