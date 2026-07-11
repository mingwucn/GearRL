from pathlib import Path

import pytest

from evaluation.scaling import ScalingEvidenceStore, ScalingProtocol
from run_scaling_study import ScalingStudyCommand


DATASET = Path("data/benchmark/curated/requirements-first-50-v2")


def test_scaling_protocol_requires_increasing_sizes_budgets_and_multiple_seeds() -> None:
    with pytest.raises(ValueError, match="sizes"):
        ScalingProtocol(tooth_domain_sizes=(5, 5))
    with pytest.raises(ValueError, match="budgets"):
        ScalingProtocol(candidate_budgets=(1000, 250))
    with pytest.raises(ValueError, match="multiple"):
        ScalingProtocol(stochastic_seeds=(1,))


def test_small_scaling_study_retains_truth_raw_runs_and_summaries(tmp_path) -> None:
    protocol = ScalingProtocol((5,), (250,), (11, 12), maximum_time_s=2.0)
    root = tmp_path / "scaling"
    path = ScalingStudyCommand().run(DATASET, root, protocol)
    manifest, cases, observations, summary = ScalingEvidenceStore().load(root)
    assert path == root / "manifest.json"
    assert manifest["case_count"] == 4
    assert len(cases) == 4
    assert {case["expected_feasible"] for case in cases} == {True, False}
    assert manifest["observation_count"] == 16
    assert len(manifest["runtime_environment"]["git_commit"]) == 40
    assert len(manifest["runtime_environment"]["environment"]["combined_sha256"]) == 64
    assert len(summary) == 3
    assert {item["method"] for item in summary} == {"exact-enumerator", "cp-sat", "differential-evolution"}
    assert all(item["full_parameter_space"] == 625 for item in summary)
    assert all("decisive_coverage_min" in item for item in summary)
    assert all("decisive_accuracy_min" in item for item in summary)


def test_scaling_store_rejects_tampering(tmp_path) -> None:
    protocol = ScalingProtocol((5,), (100,), (11, 12), maximum_time_s=2.0)
    root = tmp_path / "scaling"
    ScalingStudyCommand().run(DATASET, root, protocol)
    observations = root / "observations.json"
    observations.write_text(observations.read_text() + " ")
    with pytest.raises(ValueError, match="observations hash mismatch"):
        ScalingEvidenceStore().load(root)
