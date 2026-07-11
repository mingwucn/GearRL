import json
from pathlib import Path

from run_environmental_robustness import EnvironmentalRobustnessConfig, FrozenEnvironmentalRobustnessRunner


def test_environmental_runner_persists_housing_and_load_outcomes(tmp_path) -> None:
    config = EnvironmentalRobustnessConfig(sample_size=3, housing_erosions_mm=(0.0, 1.0), load_multipliers=(1.0, 2.0))
    bundle = FrozenEnvironmentalRobustnessRunner(tmp_path).run(Path("data/benchmark/frozen/compound-v1-frozen-400-r2"), config)
    summary = json.loads((bundle / "environmental_summary.json").read_text())
    assert len(list((bundle / "results").glob("*.json"))) == 12
    assert summary["housing_valid_rate"]["0.0"] == 1.0
    assert summary["load_valid_rate"]["1.0"] == 1.0
    assert summary["minimum_safety_factor_by_load"]["2.0"] > 1.0
