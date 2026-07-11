import json
from pathlib import Path

import pytest

from reporting.aei_submission import AEISubmissionPackageStore, AEISubmissionValidator


class TestAEISubmissionPackage:
    def test_official_numeric_constraints_and_metadata_blockers(self):
        manuscript = json.loads(Path("paper/manuscript_source.json").read_text())
        submission = json.loads(Path("paper/aei_submission_source.json").read_text())
        report = AEISubmissionValidator().validate(manuscript, submission)
        assert report["failed_constraints"] == []
        assert report["package_ready"] is False
        assert report["metadata_blockers"] == [
            "authors",
            "corresponding_author",
            "competing_interests_statement",
            "funding_statement",
            "archival_dataset_identifier",
        ]

    def test_package_is_editable_evidence_bound_and_reproducible(self, tmp_path):
        root = tmp_path / "package"
        store = AEISubmissionPackageStore()
        store.build(
            Path("paper/manuscript_source.json"),
            Path("paper/aei_submission_source.json"),
            Path("literature/aei_closest_methods.json"),
            Path("paper/generated-v4"),
            root,
        )
        validation = store.verify(root)
        store.verify_reproduction(root)
        tex = (root / "manuscript.tex").read_text()
        assert validation["package_ready"] is False
        assert r"\documentclass[preprint,12pt]{elsarticle}" in tex
        assert r"\cite{huang-2025,sun-2026}" in tex
        assert r"\section{Data Availability}" in tex
        assert len(list(root.glob("Figure_*.svg"))) == 2

    def test_package_detects_tampering(self, tmp_path):
        root = tmp_path / "package"
        store = AEISubmissionPackageStore()
        store.build(Path("paper/manuscript_source.json"), Path("paper/aei_submission_source.json"), Path("literature/aei_closest_methods.json"), Path("paper/generated-v4"), root)
        (root / "highlights.txt").write_text("altered\n")
        with pytest.raises(ValueError, match="output hash mismatch"):
            store.verify(root)
