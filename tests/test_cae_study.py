from benchmark.generator import BenchmarkGenerator
from common.design_models import MaterialLoadCase
from evaluation.cae_study import StratifiedCAEStudy


def test_stratified_cae_study_returns_every_selected_report() -> None:
    load = MaterialLoadCase("steel", 1.0, 10.0, 210_000.0, 0.3, 800.0)
    outcomes = StratifiedCAEStudy(load, 1.0).evaluate(BenchmarkGenerator().generate_compound_instances(44, 8), 4)
    assert len(outcomes) == 4
    assert all(outcome.report_count > 0 for outcome in outcomes)


def test_stratified_cae_study_uses_requested_sample_size_when_available() -> None:
    load = MaterialLoadCase("steel", 1.0, 10.0, 210_000.0, 0.3, 800.0)
    outcomes = StratifiedCAEStudy(load, 1.0).evaluate(BenchmarkGenerator().generate_compound_instances(44, 12), 12)
    assert len(outcomes) == 12
