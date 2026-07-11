import json
from pathlib import Path

import pytest

from reporting.literature_matrix import LiteratureArtifactStore, LiteratureEvidenceLoader, LiteratureMatrixRenderer


SOURCE = Path("literature/aei_closest_methods.json")


def test_literature_evidence_has_unique_traceable_methods_and_bounded_claims() -> None:
    evidence = LiteratureEvidenceLoader().load(SOURCE)
    assert len(evidence.methods) == 10
    assert {claim.status for claim in evidence.claims} == {"supported", "candidate-novelty", "unsupported"}
    rendered = LiteratureMatrixRenderer().render(evidence)
    assert "within the audited closest-method set" in rendered
    assert "universal first" in rendered
    novelty_claim = next(claim for claim in evidence.claims if claim.claim_id == "C3")
    assert "strength-coupled" not in novelty_claim.claim.lower()
    assert "proofs, and hash-bound reporting" in rendered
    assert "arbitrary mesh-graph semantics" in rendered


def test_literature_artifact_is_hash_bound_and_reproducible(tmp_path) -> None:
    root = tmp_path / "literature"
    store = LiteratureArtifactStore()
    store.build(SOURCE, root)
    manifest = store.verify(root)
    assert manifest["method_count"] == 10
    assert manifest["claim_count"] == 6
    store.verify_reproduction(root)


def test_literature_artifact_rejects_tampering(tmp_path) -> None:
    root = tmp_path / "literature"
    store = LiteratureArtifactStore()
    store.build(SOURCE, root)
    matrix = root / "AEI_CLOSEST_METHODS_MATRIX.md"
    matrix.write_text(matrix.read_text() + "unreviewed claim\n")
    with pytest.raises(ValueError, match="matrix hash mismatch"):
        store.verify(root)


def test_literature_loader_rejects_duplicate_doi(tmp_path) -> None:
    payload = json.loads(SOURCE.read_text())
    payload["methods"][1]["doi"] = payload["methods"][0]["doi"]
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="DOI records must be unique"):
        LiteratureEvidenceLoader().load(source)
