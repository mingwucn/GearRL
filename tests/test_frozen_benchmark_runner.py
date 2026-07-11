import json
from pathlib import Path

from run_certified_benchmark import CertifiedBenchmarkRunner


def test_runner_uses_frozen_dataset_without_regeneration(tmp_path) -> None:
    root = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")
    bundle = CertifiedBenchmarkRunner(tmp_path).run_frozen(root)
    summary = json.loads((bundle / "summary.json").read_text())
    assert summary["dataset_id"] == "compound-v1-frozen-400"
    assert summary["instance_count"] == 400
    assert summary["classification_accuracy"] == 1.0
