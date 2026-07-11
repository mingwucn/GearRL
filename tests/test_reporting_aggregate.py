import json

from reporting.aggregate import aggregate_bundle
from run_certified_benchmark import run


def test_aggregate_derives_metrics_from_raw_results(tmp_path) -> None:
    bundle = run(13, 2, tmp_path, infeasible_count=2)
    aggregate = aggregate_bundle(bundle)
    assert aggregate["feasible_solution_rate"] == 1.0
    assert aggregate["infeasible_rejection_rate"] == 1.0
    assert aggregate["classification_accuracy"] == 1.0
    assert aggregate["instance_count"] == 4


def test_aggregate_rejects_duplicate_result_instance_ids(tmp_path) -> None:
    bundle = run(14, 1, tmp_path)
    result = next((bundle / "results").glob("*.json"))
    duplicate = json.loads(result.read_text())
    (bundle / "results" / "duplicate.json").write_text(json.dumps(duplicate))
    try:
        aggregate_bundle(bundle)
    except ValueError as error:
        assert "unique" in str(error)
    else:
        raise AssertionError("Duplicate result identifiers must be rejected")
