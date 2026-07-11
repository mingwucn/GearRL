"""Integration contract for immutable paired-policy study artifacts."""

import json

from run_paired_policy_study import PairedPolicyStudyConfig, PairedPolicyStudyRunner


def test_runner_writes_raw_pairs_checkpoint_and_gate_summary(tmp_path) -> None:
    bundle = PairedPolicyStudyRunner(tmp_path).run(
        PairedPolicyStudyConfig(seed=8, train_instances=2, test_instances=3, imitation_epochs=100, timing_repetitions=1, bootstrap_samples=100)
    )

    summary = json.loads((bundle / "paired_summary.json").read_text())
    records = [json.loads(path.read_text()) for path in (bundle / "results").glob("*.json")]
    assert summary["observations"] == 3
    assert len(records) == 3
    assert all(record["baseline"]["valid"] for record in records)
    assert all(record["policy"]["valid"] for record in records)
    assert (bundle / "policy_state.pt").is_file()
