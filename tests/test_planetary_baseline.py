from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from benchmark.planetary_external import PublishedPlanetaryGearBrief, PublishedPlanetaryGearEvaluator
from evaluation.planetary_baseline import (
    PlanetaryBaselineBatchMerger,
    PlanetaryBaselineEvidenceStore,
    PlanetaryBaselineProtocolLoader,
    PlanetaryBaselineResult,
    PlanetaryRunOutcomeAnalyzer,
    PlanetaryDecisionDecoder,
    PlanetaryDifferentialEvolutionBaseline,
)


PROTOCOL = Path("data/protocols/planetary-baseline-v1.json")


def test_planetary_decoder_maps_integral_indices_to_source_choices() -> None:
    brief = PublishedPlanetaryGearBrief()
    candidate = PlanetaryDecisionDecoder().decode(brief, np.array([37, 22, 20, 24, 15, 87, 0, 1, 0], dtype=float))
    assert candidate.planet_count == 3
    assert candidate.module_1_mm == 2.0
    assert candidate.module_2_mm == 1.75
    assert len(PublishedPlanetaryGearEvaluator().evaluate(brief, candidate).inequality_values) == 10


def test_small_planetary_baseline_is_seeded_and_domain_valid() -> None:
    protocol = replace(PlanetaryBaselineProtocolLoader().load(PROTOCOL), population_multiplier=4, maximum_iterations=2)
    first = PlanetaryDifferentialEvolutionBaseline().solve(PublishedPlanetaryGearBrief(), protocol, 11)
    second = PlanetaryDifferentialEvolutionBaseline().solve(PublishedPlanetaryGearBrief(), protocol, 11)
    assert first.candidate == second.candidate
    assert first.evaluation == second.evaluation
    assert first.objective_calls == second.objective_calls


def test_planetary_result_round_trip() -> None:
    protocol = replace(PlanetaryBaselineProtocolLoader().load(PROTOCOL), population_multiplier=4, maximum_iterations=2)
    result = PlanetaryDifferentialEvolutionBaseline().solve(PublishedPlanetaryGearBrief(), protocol, 11)
    assert PlanetaryBaselineResult.from_json(result.to_json()) == result


def test_planetary_outcome_analysis_reports_descriptive_counts_and_termination() -> None:
    protocol = replace(PlanetaryBaselineProtocolLoader().load(PROTOCOL), seeds=(11, 12), population_multiplier=4, maximum_iterations=2)
    solver = PlanetaryDifferentialEvolutionBaseline()
    results = tuple(solver.solve(PublishedPlanetaryGearBrief(), protocol, seed) for seed in protocol.seeds)

    analysis = PlanetaryRunOutcomeAnalyzer().analyze(protocol, results)

    assert analysis["fixed_seed_run_count"] == 2
    assert "threshold_run_fraction_exact_95_interval" not in analysis
    assert "no sampling-population interval" in analysis["interpretation"]
    assert analysis["optimizer_success_count"] + analysis["iteration_limit_count"] == 2


def test_planetary_batch_merger_requires_exact_seed_coverage(tmp_path: Path) -> None:
    protocol = replace(PlanetaryBaselineProtocolLoader().load(PROTOCOL), seeds=(11, 12), population_multiplier=4, maximum_iterations=2)
    solver = PlanetaryDifferentialEvolutionBaseline()
    results = tuple(solver.solve(PublishedPlanetaryGearBrief(), protocol, seed) for seed in protocol.seeds)
    store = PlanetaryBaselineEvidenceStore()
    protocol_source = tmp_path / "protocol.json"
    protocol_source.write_text(__import__("json").dumps({"schema_version": "planetary-baseline-protocol-v1", **protocol.to_json()}))
    first, second = tmp_path / "first", tmp_path / "second"
    store.write(protocol, results[:1], protocol_source, first)
    store.write(protocol, results[1:], protocol_source, second)

    destination = tmp_path / "merged"
    PlanetaryBaselineBatchMerger().merge(protocol, (first, second), protocol_source, destination)
    assert store.verify(destination)["schema_version"] == "planetary-baseline-artifact-v1"
    with pytest.raises(ValueError, match="Duplicate planetary baseline seed"):
        PlanetaryBaselineBatchMerger().merge(protocol, (first, first, second), protocol_source, tmp_path / "duplicate")
    with pytest.raises(ValueError, match="seed coverage mismatch"):
        PlanetaryBaselineBatchMerger().merge(protocol, (first,), protocol_source, tmp_path / "incomplete")
