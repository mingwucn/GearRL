import json
from pathlib import Path

import pytest

from evaluation.replayable_proofs import ReplayableProofEvidenceStore, ReplayableProofStudy


DATASET = Path("data/benchmark/curated/requirements-first-50-v1")


def test_replayable_proof_study_covers_every_negative_case(tmp_path: Path) -> None:
    summary = ReplayableProofStudy().run(DATASET)
    assert summary["negative_case_count"] == 40
    assert all(record["proof"]["elimination_ledger"]["tuple_count"] > 0 for record in summary["records"])
    destination = tmp_path / "proofs"
    store = ReplayableProofEvidenceStore()
    store.write(summary, DATASET, destination)
    assert store.verify(destination)["schema_version"] == "replayable-negative-proofs-artifact-v1"


def test_replayable_proof_verifier_rejects_coordinated_summary_corruption(tmp_path: Path) -> None:
    summary = ReplayableProofStudy().run(DATASET)
    destination = tmp_path / "proofs"
    store = ReplayableProofEvidenceStore()
    store.write(summary, DATASET, destination)
    payload = json.loads((destination / "summary.json").read_text())
    payload["records"][0]["proof"]["elimination_ledger"]["ledger_sha256"] = "0" * 64
    summary_bytes = store._encode(payload)
    (destination / "summary.json").write_bytes(summary_bytes)
    manifest = json.loads((destination / "manifest.json").read_text())
    manifest["summary_sha256"] = __import__("hashlib").sha256(summary_bytes).hexdigest()
    (destination / "manifest.json").write_bytes(store._encode(manifest))
    with pytest.raises(ValueError, match="proof mismatch"):
        store.verify(destination)


def test_replayable_proof_study_rejects_mutated_solver_payload(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    __import__("shutil").copytree(DATASET, dataset)
    solver = next((dataset / "solver-inputs").glob("*.json"))
    solver.write_text(solver.read_text() + " ")
    with pytest.raises(ValueError, match="Curated solver hash mismatch"):
        ReplayableProofStudy().run(dataset)
