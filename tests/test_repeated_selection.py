from pathlib import Path

from evaluation.repeated_selection import OuterReplicationAnalyzer, RepeatedSelectionProtocolLoader


PROTOCOL = Path("data/protocols/repeated-selection-v1.json")


def test_repeated_selection_protocol_has_independent_outer_seed_blocks() -> None:
    protocol = RepeatedSelectionProtocolLoader().load(PROTOCOL)

    assert protocol.outer_replicates == 12
    assert protocol.training.seed != protocol.testing.seed
    assert protocol.seed_stride == 1_000_000


def test_outer_analyzer_uses_complete_train_select_test_repetitions() -> None:
    protocol = RepeatedSelectionProtocolLoader().load(PROTOCOL)
    records = [{"probability_difference": 0.01 + index * 0.00001} for index in range(protocol.outer_replicates)]

    result = OuterReplicationAnalyzer().analyze(records, protocol)

    assert result["outer_replicate_count"] == protocol.outer_replicates
    assert result["supported"]
    assert "train-select-test" in result["estimand"]
