import json

import pytest

from physics_validator.corpus import (
    ValidatorCaseCatalog,
    ValidatorCorpusFreezer,
    ValidatorCorpusLoader,
    ValidatorCorpusRunner,
)


def test_validator_catalog_has_50_unique_cases_and_ten_families() -> None:
    cases = ValidatorCaseCatalog().cases()

    assert len(cases) == 50
    assert len({case.case_id for case in cases}) == 50
    assert len({case.family for case in cases}) == 10


def test_every_authored_expectation_agrees_with_analytical_audit_and_verifier() -> None:
    records = ValidatorCorpusRunner().evaluate(ValidatorCaseCatalog().cases())

    assert len(records) == 50
    assert all(record["analytical_audit_passed"] for record in records)
    assert sum(record["expected_valid"] for record in records) == 10


def test_validator_corpus_freezes_hash_addressed_evidence(tmp_path) -> None:
    records = ValidatorCorpusRunner().evaluate(ValidatorCaseCatalog().cases())

    index_path = ValidatorCorpusFreezer().freeze(records, tmp_path / "corpus")
    index = json.loads(index_path.read_text())

    assert index["case_count"] == 50
    assert index["valid_count"] == 10
    assert index["invalid_count"] == 40
    assert index["all_analytical_audits_passed"] is True


def test_validator_corpus_loader_verifies_every_record(tmp_path) -> None:
    records = ValidatorCorpusRunner().evaluate(ValidatorCaseCatalog().cases())
    root = tmp_path / "corpus"
    ValidatorCorpusFreezer().freeze(records, root)

    corpus = ValidatorCorpusLoader().load(root)

    assert corpus.dataset_id == ValidatorCaseCatalog.VERSION
    assert len(corpus.records) == 50
    assert len(corpus.corpus_sha256) == 64


def test_validator_corpus_loader_rejects_tampering(tmp_path) -> None:
    records = ValidatorCorpusRunner().evaluate(ValidatorCaseCatalog().cases())
    root = tmp_path / "corpus"
    ValidatorCorpusFreezer().freeze(records, root)
    path = root / "cases" / "simple-valid-equal.json"
    path.write_text(path.read_text() + " ")

    with pytest.raises(ValueError, match="hash mismatch"):
        ValidatorCorpusLoader().load(root)
