import json
from pathlib import Path

import pytest

from reporting.submission_readiness import SubmissionReadinessArtifactStore, SubmissionReadinessAuditor


SOURCE = Path("paper/submission_readiness_source.json")


class TestSubmissionReadinessAuditor:
    def test_audit_is_fail_closed_and_tracks_external_gates(self):
        report = SubmissionReadinessAuditor().audit(SOURCE)
        assert report["ready_to_submit"] is False
        assert report["status_counts"]["partial"] == 2
        assert report["status_counts"]["external_pending"] == 2
        assert "planetary-conversion-review" in report["blocking_requirements"]
        assert "author-and-archival-metadata" in report["blocking_requirements"]
        if not Path("data/results/clean-environment-v2/report.json").is_file():
            assert "locked-clean-environment-attestation" in report["blocking_requirements"]

    def test_artifact_reproduces_and_detects_tampering(self, tmp_path):
        store = SubmissionReadinessArtifactStore()
        frozen = tmp_path / "frozen"
        store.build(SOURCE, frozen)
        store.verify_reproduction(frozen)
        report = json.loads((frozen / "report.json").read_text())
        assert report["target"] == "Advanced Engineering Informatics"
        (frozen / "report.json").write_text("{}\n")
        with pytest.raises(ValueError, match="report hash mismatch"):
            store.verify(frozen)
