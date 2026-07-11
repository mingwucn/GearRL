"""Integration contract for immutable frozen-sample CAE evidence."""

import json
from pathlib import Path

import pytest

from run_cae_study import FrozenCAEStudyCommand, FrozenCAEStudyConfig, FrozenCAEStudyEvidenceLoader, FrozenCAEStudyRunner


def test_runner_writes_raw_cae_outcomes_and_derived_summary(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    bundle = FrozenCAEStudyRunner(tmp_path).run(dataset, FrozenCAEStudyConfig(sample_size=8))
    summary = json.loads((bundle / "cae_summary.json").read_text())
    records = [json.loads(path.read_text()) for path in (bundle / "results").glob("*.json")]
    assert summary["observations"] == 8
    assert summary["valid_count"] == 0
    assert summary["minimum_safety_factor"] > 1.0
    assert len(records) == 8
    assert all(record["report_count"] > 0 for record in records)
    assert all(record["reports"] for record in records)
    assert all("cae_not_admission_qualified" in record["issue_codes"] for record in records)
    assert all(report["model_version"] == "involute-tooth-root-plane-stress-v3" for record in records for report in record["reports"])


def test_frozen_v3_study_retains_hash_addressed_tooth_reports(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")

    manifest_path = FrozenCAEStudyCommand().run(dataset, tmp_path / "frozen", FrozenCAEStudyConfig(sample_size=4))

    manifest = json.loads(manifest_path.read_text())
    summary = json.loads((manifest_path.parent / "summary.json").read_text())
    assert manifest["model_version"].endswith("involute-tooth-root-plane-stress-v3")
    assert len(manifest["records"]) == 4
    assert summary["report_count"] > 4
    loaded_manifest, loaded_summary, outcomes = FrozenCAEStudyEvidenceLoader().load(manifest_path.parent)
    assert loaded_manifest == manifest
    assert loaded_summary == summary
    assert len(outcomes) == 4


def test_frozen_v3_study_rejects_tampered_record(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    root = tmp_path / "frozen"
    manifest_path = FrozenCAEStudyCommand().run(dataset, root, FrozenCAEStudyConfig(sample_size=2))
    manifest = json.loads(manifest_path.read_text())
    path = root / "records" / f"{manifest['records'][0]['instance_id']}.json"
    path.write_text(path.read_text() + " ")

    with pytest.raises(ValueError, match="record hash mismatch"):
        FrozenCAEStudyEvidenceLoader().load(root)
