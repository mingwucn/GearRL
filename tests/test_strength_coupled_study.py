from pathlib import Path

import pytest

from run_strength_coupled_study import (
    StrengthCoupledEvidenceStore,
    StrengthCoupledStudyCommand,
    StrengthCoupledStudyConfig,
)


DATASET = Path("data/benchmark/curated/requirements-first-50-v1")


def test_strength_requirement_is_visible_in_solver_problem() -> None:
    requirements = StrengthCoupledStudyConfig().requirements
    assert requirements.minimum_safety_factor == 2.3
    assert requirements.load_case.material_name == "S355 (plate)"
    assert requirements.load_case.allowable_stress_mpa == pytest.approx(355.0 / 1.5)


def test_paired_study_reports_conditional_retention_and_rejection(tmp_path) -> None:
    root = tmp_path / "coupled"
    path = StrengthCoupledStudyCommand().run(DATASET, root, StrengthCoupledStudyConfig())
    manifest, summary, records = StrengthCoupledEvidenceStore().load(root)
    assert path == root / "manifest.json"
    assert summary == {
        "case_count": 10,
        "retained_count": 7,
        "redesigned_count": 0,
        "rejected_count": 3,
        "baseline_strength_admissible_count": 7,
    }
    assert "static tooth-root admission" in manifest["scope"]
    assert all(record["strength_search_complete"] for record in records if record["classification"] == "rejected")
    assert all(record["strength_minimum_safety_factor"] >= 2.3 for record in records if record["strength_train"])


def test_strength_evidence_rejects_tampering(tmp_path) -> None:
    root = tmp_path / "coupled"
    StrengthCoupledStudyCommand().run(DATASET, root, StrengthCoupledStudyConfig())
    record = next((root / "records").glob("*.json"))
    record.write_text(record.read_text() + " ")
    with pytest.raises(ValueError, match="record hash mismatch"):
        StrengthCoupledEvidenceStore().load(root)
