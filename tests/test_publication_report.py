from benchmark.generator import BenchmarkGenerator
from evaluation.comparison import CertifiedSolverComparison
from reporting.publication import PublicationReportGenerator
from synthesis.baselines import BranchAndBoundSolver, RouteFirstSolver


def test_publication_report_is_deterministic_and_derived_from_raw_outcomes() -> None:
    outcomes = CertifiedSolverComparison().evaluate(
        BenchmarkGenerator().generate_suite(21, 3, 1),
        {"branch": BranchAndBoundSolver(), "route": RouteFirstSolver()},
    )
    reporter = PublicationReportGenerator()
    summaries = reporter.summarize(outcomes, bootstrap_samples=100, seed=21)
    assert [summary.observations for summary in summaries] == [4, 4]
    table = reporter.to_markdown(summaries)
    assert "| branch |" in table
    assert "| route |" in table
