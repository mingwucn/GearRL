import json
from pathlib import Path

import pytest

from evaluation.assembly_robustness import AssemblyRobustnessEvidenceStore, AssemblyRobustnessProtocol, AssemblyRobustnessProtocolLoader, AssemblyRobustnessStudy


DATASET = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
PROTOCOL = Path("data/protocols/assembly-robustness-confirmatory-v2.json")


def test_confirmatory_protocol_is_frozen_and_resolves_pilot_saturation() -> None:
    protocol = AssemblyRobustnessProtocolLoader().load(PROTOCOL)
    assert protocol.sample_size == 120
    assert protocol.draws_per_layout == 512
    assert protocol.transverse_backlash_allowances_mm == (0.0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02)
    assert len(protocol.shaft_location_tolerances_mm) * len(protocol.housing_clearance_erosions_mm) * len(protocol.transverse_backlash_allowances_mm) == 56


def test_small_joint_robustness_study_is_seeded_and_factorial(tmp_path: Path) -> None:
    protocol = AssemblyRobustnessProtocol(
        sample_size=3,
        draws_per_layout=16,
        bootstrap_samples=20,
        shaft_location_tolerances_mm=(0.01,),
        housing_clearance_erosions_mm=(0.0,),
        transverse_backlash_allowances_mm=(0.0, 0.05),
    )
    study = AssemblyRobustnessStudy()
    first, outcomes, _, _ = study.run(DATASET, protocol)
    second, _, _, _ = study.run(DATASET, protocol)
    assert first == second
    assert first["scenario_count"] == 2
    assert first["draw_count"] == 96
    assert len(outcomes) == 96
    assert all(0 <= item["modeled_valid_probability"] <= 1 for item in first["scenarios"])


def test_evidence_store_verifies_draw_count_and_hashes(tmp_path: Path) -> None:
    protocol = AssemblyRobustnessProtocol(sample_size=2, draws_per_layout=4, bootstrap_samples=5, shaft_location_tolerances_mm=(0.01,), housing_clearance_erosions_mm=(0.0,), transverse_backlash_allowances_mm=(0.0,))
    summary, outcomes, _, _ = AssemblyRobustnessStudy().run(DATASET, protocol)
    root = tmp_path / "evidence"
    store = AssemblyRobustnessEvidenceStore()
    store.write(summary, outcomes, DATASET / "index.json", root)
    assert store.verify(root)["draw_count"] == 8
    (root / "summary.json").write_text(json.dumps({}))
    with pytest.raises(ValueError, match="summary_sha256 mismatch"):
        store.verify(root)
