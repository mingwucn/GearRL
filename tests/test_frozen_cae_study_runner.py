"""Integration contract for immutable frozen-sample CAE evidence."""

import json
from pathlib import Path

from run_cae_study import FrozenCAEStudyConfig, FrozenCAEStudyRunner


def test_runner_writes_raw_cae_outcomes_and_derived_summary(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    bundle = FrozenCAEStudyRunner(tmp_path).run(dataset, FrozenCAEStudyConfig(sample_size=8))
    summary = json.loads((bundle / "cae_summary.json").read_text())
    records = [json.loads(path.read_text()) for path in (bundle / "results").glob("*.json")]
    assert summary["observations"] == 8
    assert summary["valid_count"] == 8
    assert summary["minimum_safety_factor"] > 1.0
    assert len(records) == 8
    assert all(record["report_count"] > 0 for record in records)
