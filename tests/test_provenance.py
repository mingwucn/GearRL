import json

import pytest

from common.provenance import RunBundleStore


def test_run_bundle_records_manifest_and_prevents_result_replacement(tmp_path) -> None:
    store = RunBundleStore(tmp_path, repository_root=tmp_path)
    bundle, manifest = store.create(
        random_seed=42,
        dataset_id="benchmark-v1",
        dataset_hash="abc123",
        config={"method": "branch-and-bound"},
        model_version="certified-planar-v1",
    )
    persisted = json.loads((bundle / "manifest.json").read_text())
    assert persisted["run_id"] == manifest.run_id
    assert persisted["random_seed"] == 42
    path = store.write_result(bundle, "case-001", {"valid": True, "runtime_s": 0.5})
    assert json.loads(path.read_text())["valid"] is True
    with pytest.raises(FileExistsError):
        store.write_result(bundle, "case-001", {"valid": False})


def test_run_bundle_rejects_unsafe_instance_ids(tmp_path) -> None:
    store = RunBundleStore(tmp_path, repository_root=tmp_path)
    bundle, _ = store.create(
        random_seed=0,
        dataset_id="benchmark-v1",
        dataset_hash="hash",
        config={},
        model_version="v1",
    )
    with pytest.raises(ValueError):
        store.write_result(bundle, "../escape", {})


def test_manifest_records_environment_file_hash(tmp_path) -> None:
    environment = tmp_path / "environment.yml"
    environment.write_text("name: ai\n")
    _, manifest = RunBundleStore(tmp_path / "runs", repository_root=tmp_path, environment_file=environment).create(
        random_seed=1,
        dataset_id="benchmark-v1",
        dataset_hash="hash",
        config={},
        model_version="v1",
    )
    assert manifest.environment_hash is not None
