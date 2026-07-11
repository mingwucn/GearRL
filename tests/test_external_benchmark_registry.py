import json

import pytest

from benchmark.external import ExternalBenchmarkRegistry, ExternalCaseMetadata, ExternalSpecificationHasher


def test_registry_requires_approved_traceable_external_case(tmp_path) -> None:
    specification = {"units": "mm", "brief": "external layout"}
    metadata = ExternalCaseMetadata(
        "case-01", "https://example.org/case-01", "CC-BY-4.0", "published-cad", "reviewer-a", "approved",
        review_date="2026-07-11", reviewed_specification_sha256=ExternalSpecificationHasher.digest(specification),
    )
    path = ExternalBenchmarkRegistry(tmp_path).register(metadata, specification)
    assert json.loads(path.read_text())["metadata"]["case_id"] == "case-01"
    with pytest.raises(FileExistsError):
        ExternalBenchmarkRegistry(tmp_path).register(metadata, specification)


def test_registry_rejects_unapproved_external_case(tmp_path) -> None:
    metadata = ExternalCaseMetadata("case-02", "https://example.org/case-02", "CC-BY-4.0", "published-cad", "reviewer-a", "pending")
    with pytest.raises(ValueError):
        ExternalBenchmarkRegistry(tmp_path).register(metadata, {})


def test_registry_rejects_approval_bound_to_different_specification(tmp_path) -> None:
    reviewed = {"units": "mm", "brief": "reviewed"}
    metadata = ExternalCaseMetadata(
        "case-03", "https://example.org/case-03", "CC-BY-4.0", "published-cad", "reviewer-b", "approved",
        review_date="2026-07-11", reviewed_specification_sha256=ExternalSpecificationHasher.digest(reviewed),
    )
    with pytest.raises(ValueError, match="not bound"):
        ExternalBenchmarkRegistry(tmp_path).register(metadata, {"units": "mm", "brief": "changed"})
