"""Outer-replicated tolerance-aware selection for algorithm-level inference."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
import subprocess

import numpy as np
from scipy.stats import t

from benchmark.loader import FrozenBenchmarkLoader
from evaluation.assembly_robustness import AssemblyScenario
from evaluation.tolerance_aware_selection import (
    LayoutProbabilityEvaluator,
    NominalCompactnessSelector,
    RobustnessTrainedSelector,
    SamplingPhase,
)


@dataclass(frozen=True)
class RepeatedSelectionProtocol:
    study_id: str
    population_id: str
    partition: str
    expected_layout_count: int
    selection_size: int
    outer_replicates: int
    seed_stride: int
    shaft_location_tolerance_mm: float
    housing_clearance_erosion_mm: float
    center_distance_backlash_increment_mm: float
    training: SamplingPhase
    testing: SamplingPhase
    minimum_probability_improvement: float
    alpha: float

    def __post_init__(self) -> None:
        if self.outer_replicates < 8 or self.seed_stride < self.expected_layout_count * max(
            self.training.scramble_replicates, self.testing.scramble_replicates
        ):
            raise ValueError("Outer replication count or seed stride is insufficient")
        if not 0 < self.selection_size < self.expected_layout_count or not 0 < self.alpha < 1:
            raise ValueError("Repeated selection protocol bounds are invalid")


class RepeatedSelectionProtocolLoader:
    def load(self, path: Path) -> RepeatedSelectionProtocol:
        payload = json.loads(path.read_text())
        if payload.get("schema_version") != "repeated-selection-protocol-v1":
            raise ValueError("Unsupported repeated selection protocol")
        scenario = payload["scenario"]
        return RepeatedSelectionProtocol(
            payload["study_id"], payload["population_id"], payload["partition"],
            int(payload["expected_layout_count"]), int(payload["selection_size"]),
            int(payload["outer_replicates"]), int(payload["seed_stride"]),
            float(scenario["shaft_location_tolerance_mm"]),
            float(scenario["housing_clearance_erosion_mm"]),
            float(scenario["center_distance_backlash_increment_mm"]),
            SamplingPhase(**payload["training"]), SamplingPhase(**payload["testing"]),
            float(payload["minimum_probability_improvement"]), float(payload["alpha"]),
        )


class OuterReplicationAnalyzer:
    """Infer over independent train-select-test repetitions."""

    def analyze(self, records: list[dict], protocol: RepeatedSelectionProtocol) -> dict:
        differences = np.asarray([record["probability_difference"] for record in records], dtype=float)
        standard_error = float(differences.std(ddof=1) / sqrt(len(differences)))
        radius = float(t.ppf(1 - protocol.alpha / 2, len(differences) - 1) * standard_error)
        mean = float(differences.mean())
        interval = [mean - radius, mean + radius]
        return {
            "estimand": "mean held-out probability difference across independent train-select-test repetitions",
            "outer_replicate_count": len(records),
            "mean_probability_difference": mean,
            "standard_error": standard_error,
            "confidence_interval": interval,
            "minimum_probability_improvement": protocol.minimum_probability_improvement,
            "supported": interval[0] > protocol.minimum_probability_improvement,
        }


class RepeatedToleranceAwareSelectionStudy:
    def __init__(self) -> None:
        self._nominal = NominalCompactnessSelector()
        self._robust = RobustnessTrainedSelector()
        self._evaluator = LayoutProbabilityEvaluator()
        self._analyzer = OuterReplicationAnalyzer()

    def run(self, dataset: Path, protocol: RepeatedSelectionProtocol) -> dict:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset)
        layouts = tuple(item for item in instances if item.partition == protocol.partition and item.expected_feasible)
        if len(layouts) != protocol.expected_layout_count:
            raise ValueError("Repeated selection population mismatch")
        indices = {layout.instance_id: index for index, layout in enumerate(layouts)}
        scenario = AssemblyScenario(
            "repeated-selection-cell", protocol.shaft_location_tolerance_mm,
            protocol.housing_clearance_erosion_mm, protocol.center_distance_backlash_increment_mm,
        )
        nominal = self._nominal.select(layouts, protocol.selection_size)
        nominal_ids = tuple(item.instance_id for item in nominal)
        records = []
        for outer in range(protocol.outer_replicates):
            training_phase = replace(protocol.training, seed=protocol.training.seed + outer * protocol.seed_stride)
            testing_phase = replace(protocol.testing, seed=protocol.testing.seed + outer * protocol.seed_stride)
            training = self._evaluator.evaluate(layouts, scenario, training_phase, indices)
            training_means = {key: float(np.mean(value)) for key, value in training.items()}
            robust = self._robust.select(layouts, training_means, protocol.selection_size)
            robust_ids = tuple(item.instance_id for item in robust)
            selected = tuple({item.instance_id: item for item in (*nominal, *robust)}.values())
            testing = self._evaluator.evaluate(selected, scenario, testing_phase, indices)
            nominal_probability = float(np.asarray([testing[item] for item in nominal_ids]).mean())
            robust_probability = float(np.asarray([testing[item] for item in robust_ids]).mean())
            records.append({
                "outer_replicate": outer,
                "training_seed": training_phase.seed,
                "testing_seed": testing_phase.seed,
                "robust_selected_ids": robust_ids,
                "selection_overlap": len(set(nominal_ids) & set(robust_ids)),
                "nominal_probability": nominal_probability,
                "robust_probability": robust_probability,
                "probability_difference": robust_probability - nominal_probability,
            })
        selection_frequencies = {
            item.instance_id: sum(item.instance_id in record["robust_selected_ids"] for record in records)
            for item in layouts
        }
        return {
            "schema_version": "repeated-selection-summary-v1",
            "study_id": protocol.study_id,
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "protocol": asdict(protocol),
            "nominal_selected_ids": nominal_ids,
            "outer_records": records,
            "robust_selection_frequencies": selection_frequencies,
            "primary_inference": self._analyzer.analyze(records, protocol),
            "scope": "algorithm-level inference under one declared digital tolerance cell; not manufacturing yield",
        }


class RepeatedSelectionEvidenceStore:
    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, summary: dict, protocol_source: Path, dataset: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Repeated selection destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        summary_bytes = self._encode(summary)
        (destination / "summary.json").write_bytes(summary_bytes)
        commit = subprocess.run(("git", "rev-parse", "HEAD"), text=True, capture_output=True, check=True).stdout.strip()
        manifest = {
            "schema_version": "repeated-selection-artifact-v1",
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
            raise ValueError("Repeated selection summary hash mismatch")
        protocol_source, dataset = Path(manifest["protocol_source"]), Path(manifest["dataset"])
        if sha256(protocol_source.read_bytes()).hexdigest() != manifest["protocol_sha256"]:
            raise ValueError("Repeated selection protocol hash mismatch")
        if sha256((dataset / "index.json").read_bytes()).hexdigest() != manifest["dataset_index_sha256"]:
            raise ValueError("Repeated selection dataset hash mismatch")
        protocol = RepeatedSelectionProtocolLoader().load(protocol_source)
        if self._encode(RepeatedToleranceAwareSelectionStudy().run(dataset, protocol)) != summary_bytes:
            raise ValueError("Repeated selection semantic reproduction mismatch")
        return manifest
