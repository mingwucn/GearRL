from benchmark import CuratedBenchmarkLoader, SolverInputDirectoryLoader
from evaluation.requirements_comparison import (
    BlindRequirementsComparisonRunner,
    DifferentialEvolutionFactory,
    ExactEnumeratorFactory,
    RequirementsComparisonAdjudicator,
    RequirementsComparisonProtocol,
)


DATASET = "data/benchmark/curated/requirements-first-50-v1"


def test_comparison_uses_frozen_equal_candidate_budgets(tmp_path) -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")[:3]
    protocol = RequirementsComparisonProtocol(200, 6, (11, 12))
    root = tmp_path / "comparison"

    BlindRequirementsComparisonRunner(
        (ExactEnumeratorFactory(), DifferentialEvolutionFactory()), protocol
    ).run(views, root)

    assert (root / "exact-enumerator-seed-11.json").exists()
    assert (root / "differential-evolution-seed-11.json").exists()
    assert (root / "differential-evolution-seed-12.json").exists()


def test_comparison_adjudicator_summarizes_complete_dataset(tmp_path) -> None:
    views = SolverInputDirectoryLoader().load(f"{DATASET}/solver-inputs")
    protocol = RequirementsComparisonProtocol(7000, 8, (2026,))
    root = tmp_path / "comparison"
    BlindRequirementsComparisonRunner(
        (ExactEnumeratorFactory(), DifferentialEvolutionFactory()), protocol
    ).run(views, root)

    report = RequirementsComparisonAdjudicator().adjudicate(CuratedBenchmarkLoader().load(DATASET), root)

    assert report["methods"]["exact-enumerator"]["accuracy_min"] == 1.0
    assert report["methods"]["exact-enumerator"]["run_count"] == 1
    assert report["methods"]["differential-evolution"]["run_count"] == 1
