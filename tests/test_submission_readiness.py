import json
from pathlib import Path

import pytest

from reporting.submission_readiness import SubmissionReadinessArtifactStore, SubmissionReadinessAuditor


SOURCE = Path("paper/submission_readiness_source.json")


class TestSubmissionReadinessAuditor:
    def test_audit_is_fail_closed_and_tracks_external_gates(self):
        report = SubmissionReadinessAuditor().audit(SOURCE)
        assert report["ready_to_submit"] is False
        assert report["status_counts"] == {"passed": 11, "partial": 1, "external_pending": 2, "failed": 0}
        assert report["blocking_requirements"] == ["independent-container-attestation", "archival-release-doi"]

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
