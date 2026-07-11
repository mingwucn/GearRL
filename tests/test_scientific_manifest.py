import json
from pathlib import Path

import pytest

from reproducibility.scientific_manifest import ScientificArtifactManifestBuilder, ScientificArtifactManifestStore


CATALOG = Path("data/protocols/aei-release-artifacts-v2.json")


def test_scientific_manifest_binds_every_catalog_artifact(tmp_path: Path) -> None:
    manifest = ScientificArtifactManifestBuilder().build(CATALOG, Path.cwd())
    destination = tmp_path / "aggregate"
    store = ScientificArtifactManifestStore()
    store.write(manifest, CATALOG, destination)
    verified = store.verify(destination, Path.cwd())
    assert verified.release_id == "gearrl-aei-digital-v2"
    assert len(verified.artifacts) == len(json.loads(CATALOG.read_text())["artifacts"])


def test_scientific_manifest_rejects_duplicate_catalog_ids(tmp_path: Path) -> None:
    payload = json.loads(CATALOG.read_text())
    payload["artifacts"].append(payload["artifacts"][0])
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Duplicate scientific artifact id"):
        ScientificArtifactManifestBuilder().build(catalog, Path.cwd())


def test_scientific_manifest_rejects_catalog_artifact_changed_after_commit(tmp_path: Path) -> None:
    payload = json.loads(CATALOG.read_text())
    source = Path(payload["artifacts"][0]["path"])
    original = source.read_bytes()
    try:
        source.write_bytes(original + b" ")
        with pytest.raises(ValueError, match="not frozen at source commit"):
            ScientificArtifactManifestBuilder().build(CATALOG, Path.cwd())
    finally:
        source.write_bytes(original)
