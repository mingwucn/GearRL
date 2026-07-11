import json

import pytest

from common.provenance import create_run_bundle, write_result


def test_run_bundle_records_manifest_and_prevents_result_replacement(tmp_path) -> None:
    bundle, manifest = create_run_bundle(
        tmp_path,
        random_seed=42,
        dataset_id="benchmark-v1",
        dataset_hash="abc123",
        config={"method": "branch-and-bound"},
        model_version="certified-planar-v1",
        repository_root=tmp_path,
    )
    persisted = json.loads((bundle / "manifest.json").read_text())
    assert persisted["run_id"] == manifest.run_id
    assert persisted["random_seed"] == 42
    path = write_result(bundle, "case-001", {"valid": True, "runtime_s": 0.5})
    assert json.loads(path.read_text())["valid"] is True
    with pytest.raises(FileExistsError):
        write_result(bundle, "case-001", {"valid": False})


def test_run_bundle_rejects_unsafe_instance_ids(tmp_path) -> None:
    bundle, _ = create_run_bundle(
        tmp_path,
        random_seed=0,
        dataset_id="benchmark-v1",
        dataset_hash="hash",
        config={},
        model_version="v1",
        repository_root=tmp_path,
    )
    with pytest.raises(ValueError):
        write_result(bundle, "../escape", {})


def test_manifest_records_environment_file_hash(tmp_path) -> None:
    environment = tmp_path / "environment.yml"
    environment.write_text("name: ai\n")
    _, manifest = create_run_bundle(
        tmp_path / "runs",
        random_seed=1,
        dataset_id="benchmark-v1",
        dataset_hash="hash",
        config={},
        model_version="v1",
        repository_root=tmp_path,
        environment_file=environment,
    )
    assert manifest.environment_hash is not None
