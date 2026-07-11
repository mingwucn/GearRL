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


def test_paired_study_refuses_unqualified_strength_admission(tmp_path) -> None:
    root = tmp_path / "coupled"
    with pytest.raises(RuntimeError, match="Strength-coupled synthesis is disabled.*cae-refinement-audit-v1"):
        StrengthCoupledStudyCommand().run(DATASET, root, StrengthCoupledStudyConfig())


def test_strength_evidence_rejects_tampering(tmp_path) -> None:
    root = Path("data/results/strength-coupled-v1")
    record = next((root / "records").glob("*.json"))
    temporary = tmp_path / "coupled"
    temporary.mkdir()
    (temporary / "manifest.json").write_bytes((root / "manifest.json").read_bytes())
    (temporary / "summary.json").write_bytes((root / "summary.json").read_bytes())
    (temporary / "records").mkdir()
    for source in (root / "records").glob("*.json"):
        (temporary / "records" / source.name).write_bytes(source.read_bytes())
    target = temporary / "records" / record.name
    target.write_text(target.read_text() + " ")
    with pytest.raises(ValueError, match="record hash mismatch"):
        StrengthCoupledEvidenceStore().load(temporary)
