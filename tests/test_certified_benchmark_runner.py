import json

from run_certified_benchmark import run


def test_runner_writes_only_traceable_per_instance_results(tmp_path) -> None:
    bundle = run(5, 3, tmp_path)
    summary = json.loads((bundle / "summary.json").read_text())
    assert summary["instance_count"] == 3
    assert summary["feasible_solution_rate"] == 1.0
    assert summary["classification_accuracy"] == 1.0
    results = sorted((bundle / "results").glob("*.json"))
    assert len(results) == 3
    assert all(json.loads(path.read_text())["certificate"]["valid"] for path in results)


def test_runner_records_expected_infeasible_instances(tmp_path) -> None:
    bundle = run(6, 2, tmp_path, infeasible_count=2)
    summary = json.loads((bundle / "summary.json").read_text())
    assert summary["classification_accuracy"] == 1.0
    results = [json.loads(path.read_text()) for path in (bundle / "results").glob("*.json")]
    assert sum(not result["expected_feasible"] for result in results) == 2
