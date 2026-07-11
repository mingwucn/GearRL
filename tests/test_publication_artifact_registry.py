from pathlib import Path

import pytest

from reporting.artifact_registry import PublicationArtifactRegistry, PublicationReproducer
from run_publication_artifacts import AEIPublicationTableFactory


def test_registry_builds_four_hash_bound_evidence_tables(tmp_path) -> None:
    root = tmp_path / "paper"
    registry = PublicationArtifactRegistry()
    registry.build(root, AEIPublicationTableFactory().create())
    payload = registry.verify(root)
    assert len(payload["tables"]) == 4
    assert {item["table_id"] for item in payload["tables"]} == {
        "solver-comparison", "cae-verification", "load-uncertainty", "strength-coupling"
    }
    assert all(item["sources"] for item in payload["tables"])


def test_publication_reproduction_is_byte_identical(tmp_path) -> None:
    root = tmp_path / "paper"
    registry = PublicationArtifactRegistry()
    tables = AEIPublicationTableFactory().create()
    registry.build(root, tables)
    PublicationReproducer(registry).verify_reproduction(root, tables)


def test_registry_rejects_modified_table(tmp_path) -> None:
    root = tmp_path / "paper"
    registry = PublicationArtifactRegistry()
    registry.build(root, AEIPublicationTableFactory().create())
    table = root / "tables" / "solver-comparison.md"
    table.write_text(table.read_text() + "modified\n")
    with pytest.raises(ValueError, match="table hash mismatch"):
        registry.verify(root)
