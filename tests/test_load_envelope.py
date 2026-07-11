import json
from pathlib import Path

import pytest

from evaluation.load_envelope import AEIStaticEnvelopeCatalog
from run_load_envelope_study import LoadEnvelopeCommand, LoadEnvelopeConfig, LoadEnvelopeEvidenceStore


def test_catalog_is_factorial_sourced_and_derives_static_allowables() -> None:
    catalog = AEIStaticEnvelopeCatalog()
    cases = catalog.cases()
    assert len(cases) == 16
    assert len({case.case_id for case in cases}) == 16
    assert {case.material.grade for case in cases} == {"S355", "Toolox 44"}
    assert all(case.material.source_url.startswith("https://") for case in cases)
    assert all(
        case.load_case.allowable_stress_mpa
        == pytest.approx(case.material.minimum_yield_strength_mpa / case.material.static_screen_factor)
        for case in cases
    )


def test_frozen_envelope_is_hash_verified_and_retains_raw_reports(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    root = tmp_path / "envelope"
    manifest_path = LoadEnvelopeCommand().run(dataset, root, LoadEnvelopeConfig(sample_size=2))
    manifest, summary, outcomes = LoadEnvelopeEvidenceStore().load(root)
    assert manifest_path == root / "manifest.json"
    assert "not fatigue" in manifest["study_scope"]
    assert summary["case_count"] == 16
    assert summary["layout_case_count"] == 32
    assert len(outcomes) == 16
    assert all(outcome["layout_outcomes"] for outcome in outcomes)
    assert all(layout["reports"] for outcome in outcomes for layout in outcome["layout_outcomes"])


def test_frozen_envelope_rejects_tampering(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    root = tmp_path / "envelope"
    LoadEnvelopeCommand().run(dataset, root, LoadEnvelopeConfig(sample_size=1))
    manifest = json.loads((root / "manifest.json").read_text())
    record = root / "records" / f"{manifest['records'][0]['case_id']}.json"
    record.write_text(record.read_text() + " ")
    with pytest.raises(ValueError, match="record hash mismatch"):
        LoadEnvelopeEvidenceStore().load(root)
