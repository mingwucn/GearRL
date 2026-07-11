from pathlib import Path

import pytest

from reporting.manuscript import ManuscriptArtifactStore, ManuscriptCitationResolver, ManuscriptClaimGuard


def test_claim_guard_requires_scope_and_rejects_unsupported_claims() -> None:
    scope = "Valid under the declared kinematic, geometric, and digital evidence models."
    ManuscriptClaimGuard().validate(scope)
    with pytest.raises(ValueError, match="prohibited claims"):
        ManuscriptClaimGuard().validate(scope + " Learning improves every search.")
    with pytest.raises(ValueError, match="mandatory"):
        ManuscriptClaimGuard().validate("A broad unscoped result.")


def test_citation_resolver_requires_coverage_and_rejects_unknown_ids() -> None:
    methods = [{"id": "later", "year": 2025}, {"id": "earlier", "year": 2020}]
    resolver = ManuscriptCitationResolver(methods)
    assert resolver.resolve("Prior work [cite:later,earlier].") == "Prior work [1,2]."
    with pytest.raises(ValueError, match="missing in-text citations"):
        resolver.validate_coverage("Only [cite:earlier].")
    with pytest.raises(ValueError, match="Unknown manuscript citation"):
        resolver.resolve("Bad [cite:absent].")


def test_manuscript_is_evidence_bound_claim_guarded_and_reproducible(tmp_path) -> None:
    root = tmp_path / "manuscript"
    store = ManuscriptArtifactStore()
    store.build(
        Path("paper/manuscript_source.json"),
        Path("literature/aei_closest_methods.json"),
        Path("paper/generated-v5"),
        root,
    )
    manifest = store.verify(root)
    text = (root / "GearRL_AEI_MANUSCRIPT.md").read_text()
    assert manifest["schema_version"] == "aei-manuscript-artifact-v1"
    assert "2,048 solver-run records on 16 authored scaling cases" in text
    assert "## References" in text
    assert "[cite:" not in text
    assert "10.1016/j.aei.2023.102201" in text
    assert "## Data Availability" in text
    assert "## Declaration of Generative AI" in text
    assert "solver-scaling-largest-domain" in text
    assert "incomplete non-discoveries are unknown outcomes" in text
    assert "not topology transfer or external validity" in text
    assert "12 independent train-select-test repetitions" in text
    assert "conditional on the two realized selected layout sets" not in text.lower()
    assert all(f"RQ{index} asks" in text for index in range(1, 6))
    assert "All three solvers classified" not in text
    assert "topology-transfer case" not in text
    store.verify_reproduction(root)


def test_manuscript_store_rejects_tampering(tmp_path) -> None:
    root = tmp_path / "manuscript"
    store = ManuscriptArtifactStore()
    store.build(Path("paper/manuscript_source.json"), Path("literature/aei_closest_methods.json"), Path("paper/generated-v5"), root)
    manuscript = root / "GearRL_AEI_MANUSCRIPT.md"
    manuscript.write_text(manuscript.read_text() + "unregistered text\n")
    with pytest.raises(ValueError, match="output hash mismatch"):
        store.verify(root)
