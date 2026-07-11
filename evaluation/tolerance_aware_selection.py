"""Preregistered tolerance-aware layout selection with held-out QMC testing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import pi, sqrt
from pathlib import Path
import subprocess

import numpy as np
from scipy.stats import t

from benchmark.generator import BenchmarkInstance
from benchmark.loader import FrozenBenchmarkLoader
from evaluation.assembly_robustness import AssemblyRobustnessEvaluator, AssemblyScenario
from evaluation.confirmatory_assembly import ScrambledSobolAssemblySampler


@dataclass(frozen=True)
class SamplingPhase:
    scramble_replicates: int
    draws_per_replicate: int
    seed: int

    def __post_init__(self) -> None:
        if self.scramble_replicates < 2 or self.draws_per_replicate <= 0 or self.draws_per_replicate & (self.draws_per_replicate - 1):
            raise ValueError("Sampling phases require at least two replicates and power-of-two draws")


@dataclass(frozen=True)
class ToleranceAwareSelectionProtocol:
    study_id: str
    population_id: str
    partition: str
    expected_layout_count: int
    selection_size: int
    shaft_location_tolerance_mm: float
    housing_clearance_erosion_mm: float
    center_distance_backlash_increment_mm: float
    training: SamplingPhase
    testing: SamplingPhase
    minimum_probability_improvement: float
    alpha: float


class ToleranceAwareSelectionProtocolLoader:
    def load(self, path: Path) -> ToleranceAwareSelectionProtocol:
        payload = json.loads(path.read_text())
        if payload.get("schema_version") != "tolerance-aware-selection-protocol-v1":
            raise ValueError("Unsupported tolerance-aware selection protocol")
        scenario = payload["scenario"]
        protocol = ToleranceAwareSelectionProtocol(
            payload["study_id"], payload["population_id"], payload["partition"],
            int(payload["expected_layout_count"]), int(payload["selection_size"]),
            float(scenario["shaft_location_tolerance_mm"]), float(scenario["housing_clearance_erosion_mm"]),
            float(scenario["center_distance_backlash_increment_mm"]),
            SamplingPhase(**payload["training"]), SamplingPhase(**payload["testing"]),
            float(payload["minimum_probability_improvement"]), float(payload["alpha"]),
        )
        if not 0 < protocol.selection_size < protocol.expected_layout_count or not 0 < protocol.alpha < 1:
            raise ValueError("Tolerance-aware selection protocol bounds are invalid")
        return protocol


class LayoutCompactnessMetric:
    """Nominal policy metric independent of any perturbation outcomes."""

    def calculate(self, instance: BenchmarkInstance) -> float:
        return sum(pi * stage.outer_radius_mm() ** 2 for stage in instance.reference_train.stages)


class NominalCompactnessSelector:
    def __init__(self, metric: LayoutCompactnessMetric | None = None) -> None:
        self._metric = metric or LayoutCompactnessMetric()

    def select(self, layouts: tuple[BenchmarkInstance, ...], count: int) -> tuple[BenchmarkInstance, ...]:
        return tuple(sorted(layouts, key=lambda item: (self._metric.calculate(item), item.instance_id))[:count])


class RobustnessTrainedSelector:
    def select(self, layouts: tuple[BenchmarkInstance, ...], training_rates: dict[str, float], count: int) -> tuple[BenchmarkInstance, ...]:
        return tuple(sorted(layouts, key=lambda item: (-training_rates[item.instance_id], item.instance_id))[:count])


class LayoutProbabilityEvaluator:
    def __init__(self) -> None:
        self._sampler = ScrambledSobolAssemblySampler()
        self._evaluator = AssemblyRobustnessEvaluator()

    def evaluate(
        self,
        layouts: tuple[BenchmarkInstance, ...],
        scenario: AssemblyScenario,
        phase: SamplingPhase,
        population_indices: dict[str, int],
    ) -> dict[str, list[float]]:
        results = {}
        for instance in layouts:
            movable_count = sum(stage.id != instance.problem.input_stage_id for stage in instance.reference_train.stages)
            estimates = []
            for replicate in range(phase.scramble_replicates):
                seed = phase.seed + population_indices[instance.instance_id] * phase.scramble_replicates + replicate
                errors = self._sampler.sample(seed, phase.draws_per_replicate, movable_count)
                valid = sum(outcome.valid for outcome in self._evaluator.evaluate(instance.problem, instance.reference_train, scenario, errors))
                estimates.append(valid / phase.draws_per_replicate)
            results[instance.instance_id] = estimates
        return results


class SelectionEffectAnalyzer:
    def analyze(
        self,
        nominal_ids: tuple[str, ...],
        robust_ids: tuple[str, ...],
        test_rates: dict[str, list[float]],
        protocol: ToleranceAwareSelectionProtocol,
    ) -> dict:
        nominal = np.asarray([test_rates[item] for item in nominal_ids]).mean(axis=0)
        robust = np.asarray([test_rates[item] for item in robust_ids]).mean(axis=0)
        differences = robust - nominal
        standard_error = float(differences.std(ddof=1) / sqrt(len(differences)))
        radius = float(t.ppf(1 - protocol.alpha / 2, len(differences) - 1) * standard_error)
        interval = float(differences.mean() - radius), float(differences.mean() + radius)
        return {
            "nominal_probability": float(nominal.mean()),
            "robust_probability": float(robust.mean()),
            "probability_improvement": float(differences.mean()),
            "replicate_differences": differences.tolist(),
            "confidence_interval": list(interval),
            "minimum_probability_improvement": protocol.minimum_probability_improvement,
            "supported": interval[0] > protocol.minimum_probability_improvement,
        }


class ToleranceAwareSelectionStudy:
    def __init__(self) -> None:
        self._nominal = NominalCompactnessSelector()
        self._robust = RobustnessTrainedSelector()
        self._evaluator = LayoutProbabilityEvaluator()
        self._analyzer = SelectionEffectAnalyzer()

    def run(self, dataset: Path, protocol: ToleranceAwareSelectionProtocol) -> dict:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset)
        layouts = tuple(item for item in instances if item.partition == protocol.partition and item.expected_feasible)
        if len(layouts) != protocol.expected_layout_count:
            raise ValueError("Tolerance-aware selection population mismatch")
        indices = {layout.instance_id: index for index, layout in enumerate(layouts)}
        scenario = AssemblyScenario(
            "tolerance-aware-selection-cell", protocol.shaft_location_tolerance_mm,
            protocol.housing_clearance_erosion_mm, protocol.center_distance_backlash_increment_mm,
        )
        training = self._evaluator.evaluate(layouts, scenario, protocol.training, indices)
        training_means = {key: float(np.mean(value)) for key, value in training.items()}
        nominal = self._nominal.select(layouts, protocol.selection_size)
        robust = self._robust.select(layouts, training_means, protocol.selection_size)
        selected = tuple({item.instance_id: item for item in (*nominal, *robust)}.values())
        testing = self._evaluator.evaluate(selected, scenario, protocol.testing, indices)
        nominal_ids = tuple(item.instance_id for item in nominal)
        robust_ids = tuple(item.instance_id for item in robust)
        return {
            "schema_version": "tolerance-aware-selection-summary-v1",
            "study_id": protocol.study_id,
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "protocol": asdict(protocol),
            "population_layout_ids": [item.instance_id for item in layouts],
            "nominal_selected_ids": nominal_ids,
            "robust_selected_ids": robust_ids,
            "selection_overlap": len(set(nominal_ids) & set(robust_ids)),
            "training_mean_probabilities": training_means,
            "testing_replicate_probabilities": testing,
            "primary_inference": self._analyzer.analyze(nominal_ids, robust_ids, testing, protocol),
            "scope": "held-out digital layout selection under one declared tolerance cell; not manufacturing yield",
        }


class ToleranceAwareSelectionEvidenceStore:
    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, summary: dict, protocol_source: Path, dataset: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Tolerance-aware selection destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        summary_bytes = self._encode(summary)
        (destination / "summary.json").write_bytes(summary_bytes)
        commit = subprocess.run(("git", "rev-parse", "HEAD"), text=True, capture_output=True, check=True).stdout.strip()
        manifest = {
            "schema_version": "tolerance-aware-selection-artifact-v1",
            "source_commit": commit,
            "protocol_source": str(protocol_source),
            "protocol_sha256": sha256(protocol_source.read_bytes()).hexdigest(),
            "dataset": str(dataset),
            "dataset_index_sha256": sha256((dataset / "index.json").read_bytes()).hexdigest(),
            "summary_sha256": sha256(summary_bytes).hexdigest(),
        }
        path = destination / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        summary_bytes = (destination / "summary.json").read_bytes()
        if sha256(summary_bytes).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Tolerance-aware selection summary hash mismatch")
        protocol_source, dataset = Path(manifest["protocol_source"]), Path(manifest["dataset"])
        if sha256(protocol_source.read_bytes()).hexdigest() != manifest["protocol_sha256"]:
            raise ValueError("Tolerance-aware selection protocol hash mismatch")
        if sha256((dataset / "index.json").read_bytes()).hexdigest() != manifest["dataset_index_sha256"]:
            raise ValueError("Tolerance-aware selection dataset hash mismatch")
        protocol = ToleranceAwareSelectionProtocolLoader().load(protocol_source)
        reproduced = self._encode(ToleranceAwareSelectionStudy().run(dataset, protocol))
        if reproduced != summary_bytes:
            raise ValueError("Tolerance-aware selection semantic reproduction mismatch")
        return manifest
