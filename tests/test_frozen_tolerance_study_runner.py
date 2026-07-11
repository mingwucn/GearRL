"""Integration contract for immutable frozen tolerance evidence."""

import json
from pathlib import Path

from run_tolerance_study import FrozenToleranceStudyConfig, FrozenToleranceStudyRunner


def test_runner_records_every_selected_instance_and_offset(tmp_path) -> None:
    dataset = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    config = FrozenToleranceStudyConfig(sample_size=4, offsets_mm=(0.0, 0.01))
    bundle = FrozenToleranceStudyRunner(tmp_path).run(dataset, config)
    summary = json.loads((bundle / "tolerance_summary.json").read_text())
    assert len(list((bundle / "results").glob("*.json"))) == 8
    assert summary["valid_rate_by_offset_mm"]["0.0"] == 1.0
    assert summary["valid_rate_by_offset_mm"]["0.01"] == 0.0
