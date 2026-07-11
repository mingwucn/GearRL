import json

import pytest

from benchmark import CuratedBenchmarkLoader, SolverInputDirectoryLoader
from evaluation.blind_synthesis import BlindAdjudicator, BlindPredictionStore, BlindSynthesisExperiment
from synthesis import EnumerativeCompoundSynthesizer, ProductionCandidateValidator


DATASET = "data/benchmark/curated/requirements-first-50-v1"


def test_solver_input_loader_round_trips_typed_views_without_evidence() -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")

    assert len(views) == 50
    assert all("expected_feasible" not in repr(view.to_json()) for view in views)
    assert all("reference_train" not in repr(view.to_json()) for view in views)


def test_blind_solver_predicts_curated_cases_without_evidence_access(tmp_path) -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")
    solver = EnumerativeCompoundSynthesizer(ProductionCandidateValidator())

    predictions = BlindSynthesisExperiment(solver).run(views)
    path = BlindPredictionStore().write(predictions, tmp_path / "predictions.json")

    assert len(predictions) == 50
    assert all("expected_feasible" not in repr(prediction.to_json()) for prediction in predictions)
    assert BlindPredictionStore().read(path)


def test_adjudication_occurs_only_after_predictions_are_sealed(tmp_path) -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")
    predictions = BlindSynthesisExperiment(EnumerativeCompoundSynthesizer(ProductionCandidateValidator())).run(views)
    path = BlindPredictionStore().write(predictions, tmp_path / "predictions.json")
    dataset = CuratedBenchmarkLoader().load(DATASET)

    report = BlindAdjudicator().adjudicate(dataset, path)

    assert report.prediction_count == 50
    assert report.correct_count == 50
    assert report.feasible_true_positive_count == 10
    assert report.infeasible_true_negative_count == 40
    assert report.accuracy == 1.0


def test_adjudicator_rejects_prediction_id_mismatch(tmp_path) -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")[:1]
    predictions = BlindSynthesisExperiment(EnumerativeCompoundSynthesizer(ProductionCandidateValidator())).run(views)
    path = BlindPredictionStore().write(predictions, tmp_path / "predictions.json")

    with pytest.raises(ValueError, match="id mismatch"):
        BlindAdjudicator().adjudicate(CuratedBenchmarkLoader().load(DATASET), path)


def test_prediction_store_detects_record_tampering(tmp_path) -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")[:1]
    prediction = BlindSynthesisExperiment(EnumerativeCompoundSynthesizer(ProductionCandidateValidator())).run(views)
    path = BlindPredictionStore().write(prediction, tmp_path / "predictions.json")
    payload = json.loads(path.read_text())
    payload["records"][0]["predicted_feasible"] = not payload["records"][0]["predicted_feasible"]
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="hash mismatch"):
        BlindPredictionStore().read(path)
