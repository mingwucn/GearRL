import json
from pathlib import Path

import pytest

from reproducibility.scientific_manifest import ScientificArtifactManifestBuilder, ScientificArtifactManifestStore


CATALOG = Path("data/protocols/aei-release-artifacts-v1.json")


def test_scientific_manifest_binds_every_catalog_artifact(tmp_path: Path) -> None:
    manifest = ScientificArtifactManifestBuilder().build(CATALOG, Path.cwd())
    destination = tmp_path / "aggregate"
    store = ScientificArtifactManifestStore()
    store.write(manifest, CATALOG, destination)
    verified = store.verify(destination, Path.cwd())
    assert verified.release_id == "gearrl-aei-digital-v1"
    assert len(verified.artifacts) == len(json.loads(CATALOG.read_text())["artifacts"])


def test_scientific_manifest_rejects_duplicate_catalog_ids(tmp_path: Path) -> None:
    payload = json.loads(CATALOG.read_text())
    payload["artifacts"].append(payload["artifacts"][0])
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Duplicate scientific artifact id"):
        ScientificArtifactManifestBuilder().build(catalog, Path.cwd())
