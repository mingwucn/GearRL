from dataclasses import replace
from pathlib import Path

import numpy as np

from benchmark.planetary_external import PublishedPlanetaryGearBrief, PublishedPlanetaryGearEvaluator
from evaluation.planetary_baseline import PlanetaryBaselineProtocolLoader, PlanetaryDecisionDecoder, PlanetaryDifferentialEvolutionBaseline


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
