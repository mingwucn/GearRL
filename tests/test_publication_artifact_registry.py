from pathlib import Path

import pytest

from reporting.artifact_registry import PublicationArtifactRegistry, PublicationReproducer
from run_publication_artifacts import AEIPublicationFigureFactory, AEIPublicationTableFactory


def test_registry_builds_hash_bound_evidence_tables_and_figures(tmp_path) -> None:
    root = tmp_path / "paper"
    registry = PublicationArtifactRegistry()
    registry.build(root, AEIPublicationTableFactory().create(), AEIPublicationFigureFactory().create())
    payload = registry.verify(root)
    assert len(payload["tables"]) == 6
    assert {item["table_id"] for item in payload["tables"]} == {
        "solver-comparison",
        "cae-qualification",
        "knowledge-ablation",
        "planetary-baseline",
        "solver-scaling-largest-domain",
        "assembly-robustness",
    }
    assert all(item["sources"] for item in payload["tables"])
    assert len(payload["figures"]) == 3
    assert all((root / item["output"]).read_bytes().startswith(b'<?xml version="1.0"') for item in payload["figures"])


def test_publication_reproduction_is_byte_identical(tmp_path) -> None:
    root = tmp_path / "paper"
    registry = PublicationArtifactRegistry()
    tables = AEIPublicationTableFactory().create()
    figures = AEIPublicationFigureFactory().create()
    registry.build(root, tables, figures)
    PublicationReproducer(registry).verify_reproduction(root, tables, figures)


def test_registry_rejects_modified_table(tmp_path) -> None:
    root = tmp_path / "paper"
    registry = PublicationArtifactRegistry()
    registry.build(root, AEIPublicationTableFactory().create(), AEIPublicationFigureFactory().create())
    table = root / "tables" / "solver-comparison.md"
    table.write_text(table.read_text() + "modified\n")
    with pytest.raises(ValueError, match="table hash mismatch"):
        registry.verify(root)
