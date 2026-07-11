"""Two-process blind synthesis and evaluator-only adjudication workflow."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from benchmark.curated import FrozenCuratedDataset
from benchmark.specification import SolverBenchmarkView
from synthesis.requirements_solver import RequirementsFirstSynthesisSolver


@dataclass(frozen=True)
class BlindPrediction:
    """One sealed prediction containing no expected outcome or oracle record."""

    instance_id: str
    predicted_feasible: bool
    runtime_s: float
    parameter_tuples_evaluated: int
    placements_evaluated: int
    search_complete: bool
    train: dict | None
    certificate: dict | None

    def to_json(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "predicted_feasible": self.predicted_feasible,
            "runtime_s": self.runtime_s,
            "parameter_tuples_evaluated": self.parameter_tuples_evaluated,
            "placements_evaluated": self.placements_evaluated,
            "search_complete": self.search_complete,
            "train": self.train,
            "certificate": self.certificate,
        }


class BlindSynthesisExperiment:
    """Run a solver over views whose type excludes all evaluator evidence."""

    def __init__(self, solver: RequirementsFirstSynthesisSolver):
        self._solver = solver

    def run(self, views: tuple[SolverBenchmarkView, ...]) -> tuple[BlindPrediction, ...]:
        predictions = []
        for view in views:
            started = perf_counter()
            result = self._solver.solve(view)
            runtime = perf_counter() - started
            predictions.append(
                BlindPrediction(
                    view.instance_id,
                    result.train is not None,
                    runtime,
                    result.parameter_tuples_evaluated,
                    result.placements_evaluated,
                    result.search_complete,
                    result.train.to_json() if result.train else None,
                    result.certificate.to_json() if result.certificate else None,
                )
            )
        return tuple(predictions)


class BlindPredictionStore:
    """Write-once persistence for predictions sealed before adjudication."""

    def write(self, predictions: tuple[BlindPrediction, ...], destination: str | Path) -> Path:
        path = Path(destination)
        if path.exists():
            raise FileExistsError(f"Blind prediction artifact already exists: {path}")
        if not predictions or len({prediction.instance_id for prediction in predictions}) != len(predictions):
            raise ValueError("Blind predictions must be non-empty with unique instance ids")
        path.parent.mkdir(parents=True, exist_ok=True)
        records = [prediction.to_json() for prediction in predictions]
        record_bytes = self._encode(records)
        payload = {
            "schema_version": "blind-predictions-v1",
            "prediction_count": len(records),
            "records_sha256": hashlib.sha256(record_bytes).hexdigest(),
            "records": records,
        }
        path.write_bytes(self._encode(payload))
        return path

    def read(self, source: str | Path) -> tuple[dict, ...]:
        payload = json.loads(Path(source).read_bytes())
        records = payload["records"]
        if payload["schema_version"] != "blind-predictions-v1" or payload["prediction_count"] != len(records):
            raise ValueError("Invalid blind prediction schema or count")
        if hashlib.sha256(self._encode(records)).hexdigest() != payload["records_sha256"]:
            raise ValueError("Blind prediction record hash mismatch")
        if len({record["instance_id"] for record in records}) != len(records):
            raise ValueError("Blind prediction ids must be unique")
        return tuple(records)

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


@dataclass(frozen=True)
class BlindAdjudicationReport:
    dataset_id: str
    prediction_count: int
    correct_count: int
    feasible_true_positive_count: int
    infeasible_true_negative_count: int
    accuracy: float
    unknown_count: int
    decisive_coverage: float
    decisive_accuracy: float
    prediction_artifact_sha256: str

    def to_json(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "prediction_count": self.prediction_count,
            "correct_count": self.correct_count,
            "feasible_true_positive_count": self.feasible_true_positive_count,
            "infeasible_true_negative_count": self.infeasible_true_negative_count,
            "accuracy": self.accuracy,
            "unknown_count": self.unknown_count,
            "decisive_coverage": self.decisive_coverage,
            "decisive_accuracy": self.decisive_accuracy,
            "prediction_artifact_sha256": self.prediction_artifact_sha256,
        }


class BlindAdjudicator:
    """Join sealed predictions with evaluator-only labels after synthesis ends."""

    def adjudicate(self, dataset: FrozenCuratedDataset, predictions_path: str | Path) -> BlindAdjudicationReport:
        path = Path(predictions_path)
        predictions = BlindPredictionStore().read(path)
        expected = {payload["instance_id"]: bool(payload["expected_feasible"]) for payload in dataset.evidence_payloads}
        predicted = {record["instance_id"]: bool(record["predicted_feasible"]) for record in predictions}
        complete = {record["instance_id"]: bool(record["search_complete"]) for record in predictions}
        if set(expected) != set(predicted):
            missing = sorted(set(expected) - set(predicted))
            extra = sorted(set(predicted) - set(expected))
            raise ValueError(f"Prediction/evidence id mismatch; missing={missing}, extra={extra}")
        correct = sum(
            (predicted[instance_id] and label) or (not predicted[instance_id] and not label and complete[instance_id])
            for instance_id, label in expected.items()
        )
        true_positive = sum(predicted[instance_id] and label for instance_id, label in expected.items())
        true_negative = sum(not predicted[instance_id] and not label and complete[instance_id] for instance_id, label in expected.items())
        unknown = sum(not predicted[instance_id] and not complete[instance_id] for instance_id in expected)
        decisive = len(predictions) - unknown
        return BlindAdjudicationReport(
            dataset.dataset_id,
            len(predictions),
            correct,
            true_positive,
            true_negative,
            correct / len(predictions),
            unknown,
            decisive / len(predictions),
            correct / decisive if decisive else 0.0,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )

    def write(self, report: BlindAdjudicationReport, destination: str | Path) -> Path:
        path = Path(destination)
        if path.exists():
            raise FileExistsError(f"Blind adjudication artifact already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n")
        return path
