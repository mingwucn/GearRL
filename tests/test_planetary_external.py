import json
from pathlib import Path

from benchmark.planetary_external import PlanetaryGearCandidate, PublishedPlanetaryGearBrief, PublishedPlanetaryGearEvaluator


def test_published_planetary_brief_matches_frozen_pending_conversion() -> None:
    brief = PublishedPlanetaryGearBrief()
    frozen = json.loads(Path("data/external/pending/mahdy-2023-planetary-gear-train.json").read_text())
    assert frozen["metadata"]["source_doi"] == brief.source_doi
    assert frozen["target_ratios"] == list(brief.target_ratios)
    assert frozen["constraint_count"] == 11
    assert frozen["metadata"]["conversion_status"] == "pending-independent-review"


def test_planetary_evaluator_rejects_domain_and_assembly_violations() -> None:
    evaluator = PublishedPlanetaryGearEvaluator()
    brief = PublishedPlanetaryGearBrief()
    outside = evaluator.evaluate(brief, PlanetaryGearCandidate(16, 20, 20, 20, 20, 80, 3, 2.0, 2.0))
    assert not outside.valid and outside.issue_codes == ("tooth_bound",)
    candidate = PlanetaryGearCandidate(37, 22, 20, 24, 15, 87, 4, 2.0, 1.75)
    evaluated = evaluator.evaluate(brief, candidate)
    assert not evaluated.valid
    assert "h1_assembly_divisibility" in evaluated.issue_codes


def test_planetary_ratio_model_includes_reverse_ratio_sign() -> None:
    candidate = PlanetaryGearCandidate(37, 22, 20, 24, 15, 87, 3, 2.0, 1.75)
    result = PublishedPlanetaryGearEvaluator().evaluate(PublishedPlanetaryGearBrief(), candidate)
    assert result.ratios[0] > 0
    assert result.ratios[1] > 0
    assert result.ratios[2] < 0
    assert len(result.inequality_values) == 10
