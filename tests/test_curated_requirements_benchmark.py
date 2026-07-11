import json

import pytest

from benchmark import (
    CuratedBenchmarkFreezer,
    CuratedBenchmarkLoader,
    CuratedCaseCatalog,
    CuratedRequirementsFirstFactory,
    ExactCompoundTrainOracle,
)
from physics_validator.reference_verifier import ReferenceVerifier


def test_catalog_contains_50_explicit_unique_cases_across_five_categories() -> None:
    definitions = CuratedCaseCatalog().definitions()

    assert len(definitions) == 50
    assert len({definition.case_id for definition in definitions}) == 50
    assert {definition.category for definition in definitions} == {
        "analytical-feasible",
        "ratio-infeasible",
        "shaft-spacing-infeasible",
        "obstacle-infeasible",
        "boundary-infeasible",
    }


def test_every_curated_label_has_independent_global_evidence() -> None:
    cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()

    assert all(case.evidence.globally_proven for case in cases)
    assert any(case.evidence.expected_feasible for case in cases)
    assert any(not case.evidence.expected_feasible for case in cases)


def test_independent_feasible_witnesses_agree_with_production_verifier() -> None:
    cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()
    feasible = [case for case in cases if case.evidence.expected_feasible]

    certificates = [
        ReferenceVerifier.verify(case.solver_view.specification.problem, case.evidence.reference_train)
        for case in feasible
    ]

    assert len(certificates) == 10
    assert all(certificate.valid for certificate in certificates)
    assert all(certificate.model_version == "certified-planar-v3" for certificate in certificates)


def test_freezer_physically_separates_solver_inputs_from_evidence(tmp_path) -> None:
    cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()

    index_path = CuratedBenchmarkFreezer().freeze(cases, tmp_path / "curated")
    index = json.loads(index_path.read_text())
    solver_payload = (index_path.parent / "solver-inputs" / f"{cases[0].solver_view.instance_id}.json").read_text()

    assert index["instance_count"] == 50
    assert index["all_labels_globally_proven"] is True
    assert "reference_train" not in solver_payload
    assert "expected_feasible" not in solver_payload
    assert (index_path.parent / "evaluator-only" / f"{cases[0].solver_view.instance_id}.json").exists()


def test_loader_verifies_and_keeps_payload_sets_separate(tmp_path) -> None:
    cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()
    root = tmp_path / "curated"
    CuratedBenchmarkFreezer().freeze(cases, root)

    dataset = CuratedBenchmarkLoader().load(root)

    assert dataset.dataset_id == CuratedCaseCatalog.VERSION
    assert len(dataset.solver_payloads) == len(dataset.evidence_payloads) == 50
    assert all("expected_feasible" not in payload for payload in dataset.solver_payloads)
    assert len(dataset.dataset_sha256) == 64


def test_loader_rejects_tampered_solver_payload(tmp_path) -> None:
    cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()
    root = tmp_path / "curated"
    CuratedBenchmarkFreezer().freeze(cases, root)
    path = root / "solver-inputs" / f"{cases[0].solver_view.instance_id}.json"
    path.write_text(path.read_text() + " ")

    with pytest.raises(ValueError, match="solver hash mismatch"):
        CuratedBenchmarkLoader().load(root)


def test_loader_rejects_coordinated_truth_flag_and_hash_tampering(tmp_path) -> None:
    cases = CuratedRequirementsFirstFactory(ExactCompoundTrainOracle()).build()
    root = tmp_path / "curated"
    index_path = CuratedBenchmarkFreezer().freeze(cases, root)
    index = json.loads(index_path.read_text())
    instance_id = "ratio-none-01"
    evidence_path = root / "evaluator-only" / f"{instance_id}.json"
    evidence = json.loads(evidence_path.read_text())
    evidence["expected_feasible"] = True
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    record = next(item for item in index["instances"] if item["instance_id"] == instance_id)
    import hashlib
    record["evidence_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")

    with pytest.raises(ValueError, match="recomputed label mismatch"):
        CuratedBenchmarkLoader().load(root)
