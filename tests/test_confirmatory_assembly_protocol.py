from dataclasses import replace
from pathlib import Path

import pytest

from benchmark.loader import FrozenBenchmarkLoader
from evaluation.confirmatory_assembly import ConfirmatoryAssemblyProtocolLoader, HeldOutFeasibleLayoutCensus


PROTOCOL = Path("data/protocols/assembly-robustness-confirmatory-v3.json")
DATASET = Path("data/benchmark/frozen/compound-v1-frozen-400-r2")


def test_v3_protocol_predeclares_population_computation_and_hypotheses() -> None:
    protocol = ConfirmatoryAssemblyProtocolLoader().load(PROTOCOL)
    assert protocol.partition == "test"
    assert protocol.expected_layout_count == 120
    assert protocol.scramble_replicates == 8
    assert protocol.draws_per_replicate == 1024
    assert len(protocol.cells) == 8
    assert protocol.declared_draw_count == 7_864_320
    assert protocol.interaction.maximum_interaction == -0.01
    assert protocol.housing_equivalence.equivalence_margin == 0.001


def test_v3_population_is_the_complete_feasible_test_census() -> None:
    protocol = ConfirmatoryAssemblyProtocolLoader().load(PROTOCOL)
    _, _, instances = FrozenBenchmarkLoader().load(DATASET)
    selected = HeldOutFeasibleLayoutCensus().select(instances, protocol)
    assert len(selected) == 120
    assert all(instance.partition == "test" and instance.expected_feasible for instance in selected)
    assert {instance.family for instance in selected} == {
        "compound-square",
        "compound-wide",
        "compound-tall",
        "compound-chamfered",
        "adversarial-tight-clearance",
    }


def test_protocol_rejects_non_power_of_two_qmc_draw_count() -> None:
    protocol = ConfirmatoryAssemblyProtocolLoader().load(PROTOCOL)
    with pytest.raises(ValueError, match="power of two"):
        replace(protocol, draws_per_replicate=1000)


def test_population_census_fails_on_cardinality_drift() -> None:
    protocol = replace(ConfirmatoryAssemblyProtocolLoader().load(PROTOCOL), expected_layout_count=119)
    _, _, instances = FrozenBenchmarkLoader().load(DATASET)
    with pytest.raises(ValueError, match="population mismatch"):
        HeldOutFeasibleLayoutCensus().select(instances, protocol)
