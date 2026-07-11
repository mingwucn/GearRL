import json
from hashlib import sha256
from pathlib import Path

import pytest

from benchmark import ReplayableExactCompoundTrainOracle, SolverInputDirectoryLoader
from evaluation.replayable_proofs import ReplayableProofEvidenceStore, ReplayableProofStudy


DATASET = Path("data/benchmark/curated/requirements-first-50-v2")


def rewrite_summary_and_manifest(store: ReplayableProofEvidenceStore, destination: Path, payload: dict) -> None:
    summary_bytes = store._encode(payload)
    (destination / "summary.json").write_bytes(summary_bytes)
    manifest = json.loads((destination / "manifest.json").read_text())
    manifest["summary_sha256"] = sha256(summary_bytes).hexdigest()
    (destination / "manifest.json").write_bytes(store._encode(manifest))


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
    rewrite_summary_and_manifest(store, destination, payload)
    with pytest.raises(ValueError, match="proof mismatch"):
        store.verify(destination)


def test_replayable_proof_verifier_rejects_coordinated_deletion_and_count_rewrite(tmp_path: Path) -> None:
    store = ReplayableProofEvidenceStore()
    destination = tmp_path / "proofs"
    store.write(ReplayableProofStudy().run(DATASET), DATASET, destination)
    payload = json.loads((destination / "summary.json").read_text())
    payload["records"].pop()
    payload["negative_case_count"] = len(payload["records"])
    rewrite_summary_and_manifest(store, destination, payload)

    with pytest.raises(ValueError, match="negative subject coverage mismatch"):
        store.verify(destination)


def test_replayable_proof_verifier_rejects_duplicate_subject(tmp_path: Path) -> None:
    store = ReplayableProofEvidenceStore()
    destination = tmp_path / "proofs"
    store.write(ReplayableProofStudy().run(DATASET), DATASET, destination)
    payload = json.loads((destination / "summary.json").read_text())
    payload["records"][1] = payload["records"][0]
    rewrite_summary_and_manifest(store, destination, payload)

    with pytest.raises(ValueError, match="duplicate subjects"):
        store.verify(destination)


def test_replayable_proof_verifier_rejects_positive_case_substitution(tmp_path: Path) -> None:
    store = ReplayableProofEvidenceStore()
    destination = tmp_path / "proofs"
    store.write(ReplayableProofStudy().run(DATASET), DATASET, destination)
    positive = next(
        view
        for view in SolverInputDirectoryLoader().load(DATASET / "solver-inputs")
        if view.instance_id.startswith("valid-")
    )
    positive_proof = ReplayableExactCompoundTrainOracle().solve(positive).proof
    payload = json.loads((destination / "summary.json").read_text())
    payload["records"][0] = {"instance_id": positive.instance_id, "proof": positive_proof.to_json()}
    rewrite_summary_and_manifest(store, destination, payload)

    with pytest.raises(ValueError, match="negative subject coverage mismatch"):
        store.verify(destination)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (("feasible", True, "not infeasible"), ("design_space_complete", False, "not complete")),
)
def test_replayable_proof_verifier_requires_complete_infeasible_status(
    tmp_path: Path, field: str, value: bool, message: str
) -> None:
    store = ReplayableProofEvidenceStore()
    destination = tmp_path / "proofs"
    store.write(ReplayableProofStudy().run(DATASET), DATASET, destination)
    payload = json.loads((destination / "summary.json").read_text())
    payload["records"][0]["proof"][field] = value
    rewrite_summary_and_manifest(store, destination, payload)

    with pytest.raises(ValueError, match=message):
        store.verify(destination)


def test_replayable_proof_study_rejects_mutated_solver_payload(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    __import__("shutil").copytree(DATASET, dataset)
    solver = next((dataset / "solver-inputs").glob("*.json"))
    solver.write_text(solver.read_text() + " ")
    with pytest.raises(ValueError, match="Curated solver hash mismatch"):
        ReplayableProofStudy().run(dataset)
