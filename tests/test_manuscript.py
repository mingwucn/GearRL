from pathlib import Path

import pytest

from reporting.manuscript import ManuscriptArtifactStore, ManuscriptCitationResolver, ManuscriptClaimGuard


def test_claim_guard_requires_scope_and_rejects_unsupported_claims() -> None:
    scope = "Valid under the declared kinematic, geometric, and static-strength model."
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
        Path("paper/generated-v1"),
        root,
    )
    manifest = store.verify(root)
    text = (root / "GearRL_AEI_MANUSCRIPT.md").read_text()
    assert manifest["schema_version"] == "aei-manuscript-artifact-v1"
    assert "2,048 observations" in text
    assert "## References" in text
    assert "[8,10]" in text
    assert "## Data Availability" in text
    assert "## Declaration of Generative AI" in text
    assert "solver-scaling-largest-domain" in text
    store.verify_reproduction(root)


def test_manuscript_store_rejects_tampering(tmp_path) -> None:
    root = tmp_path / "manuscript"
    store = ManuscriptArtifactStore()
    store.build(Path("paper/manuscript_source.json"), Path("literature/aei_closest_methods.json"), Path("paper/generated-v1"), root)
    manuscript = root / "GearRL_AEI_MANUSCRIPT.md"
    manuscript.write_text(manuscript.read_text() + "unregistered text\n")
    with pytest.raises(ValueError, match="output hash mismatch"):
        store.verify(root)
