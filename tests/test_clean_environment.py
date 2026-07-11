from pathlib import Path

import pytest

from reproducibility.clean_environment import CleanEnvironmentAttestor, CleanEnvironmentEvidenceStore, SourceTreeHasher


def test_source_tree_hash_is_path_and_content_sensitive(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "value.txt").write_text("one")
    hasher = SourceTreeHasher()
    original = hasher.digest(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("changing metadata")
    assert hasher.digest(tmp_path) == original
    (tmp_path / "a" / "value.txt").write_text("two")
    assert hasher.digest(tmp_path) != original


def test_evidence_store_requires_complete_success(tmp_path: Path) -> None:
    store = CleanEnvironmentEvidenceStore()
    root = tmp_path / "evidence"
    report = {"all_commands_passed": True, "verification_count": len(CleanEnvironmentAttestor.VERIFICATIONS), "source_commit": "abc"}
    store.write(report, root)
    assert store.verify(root)["source_commit"] == "abc"
    (root / "report.json").write_text("{}\n")
    with pytest.raises(ValueError, match="report hash mismatch"):
        store.verify(root)
