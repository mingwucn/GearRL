import json
from pathlib import Path

from run_backlash_study import BacklashStudyConfig, FrozenBacklashStudyRunner


def test_backlash_runner_persists_declared_response_surface(tmp_path) -> None:
    config = BacklashStudyConfig(sample_size=3, allowances_mm=(0.0, 0.1), expansions_mm=(0.0, 0.01))
    bundle = FrozenBacklashStudyRunner(tmp_path).run(Path("data/benchmark/frozen/compound-v1-frozen-400-r2"), config)
    summary = json.loads((bundle / "backlash_summary.json").read_text())
    assert len(list((bundle / "results").glob("*.json"))) == 12
    assert summary["valid_rate_surface"]["allowance=0.0,expansion=0.0"] == 1.0
    assert summary["valid_rate_surface"]["allowance=0.0,expansion=0.01"] == 0.0
    assert summary["valid_rate_surface"]["allowance=0.1,expansion=0.01"] == 1.0
