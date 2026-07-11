from pathlib import Path

import numpy as np

from evaluation.tolerance_aware_selection import SelectionEffectAnalyzer, ToleranceAwareSelectionProtocolLoader


PROTOCOL = Path("data/protocols/tolerance-aware-selection-v1.json")


def test_tolerance_selection_protocol_separates_training_and_testing() -> None:
    protocol = ToleranceAwareSelectionProtocolLoader().load(PROTOCOL)
    assert protocol.training.seed != protocol.testing.seed
    assert protocol.selection_size == 10
    assert protocol.testing.scramble_replicates == 8


def test_selection_effect_analyzer_applies_predeclared_threshold() -> None:
    protocol = ToleranceAwareSelectionProtocolLoader().load(PROTOCOL)
    nominal_ids, robust_ids = ("n1", "n2"), ("r1", "r2")
    base = np.linspace(0.01, 0.011, protocol.testing.scramble_replicates).tolist()
    improved = (np.asarray(base) + 0.01).tolist()
    rates = {"n1": base, "n2": base, "r1": improved, "r2": improved}
    result = SelectionEffectAnalyzer().analyze(nominal_ids, robust_ids, rates, protocol)
    assert result["supported"]
    assert result["confidence_interval"][0] > protocol.minimum_probability_improvement
