import json

import pytest

from benchmark.external import ExternalBenchmarkRegistry, ExternalCaseMetadata


def test_registry_requires_approved_traceable_external_case(tmp_path) -> None:
    metadata = ExternalCaseMetadata("case-01", "https://example.org/case-01", "CC-BY-4.0", "published-cad", "reviewer-a", "approved")
    path = ExternalBenchmarkRegistry(tmp_path).register(metadata, {"units": "mm", "brief": "external layout"})
    assert json.loads(path.read_text())["metadata"]["case_id"] == "case-01"
    with pytest.raises(FileExistsError):
        ExternalBenchmarkRegistry(tmp_path).register(metadata, {})


def test_registry_rejects_unapproved_external_case(tmp_path) -> None:
    metadata = ExternalCaseMetadata("case-02", "https://example.org/case-02", "CC-BY-4.0", "published-cad", "reviewer-a", "pending")
    with pytest.raises(ValueError):
        ExternalBenchmarkRegistry(tmp_path).register(metadata, {})
