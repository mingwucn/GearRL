"""Governance for externally sourced benchmark cases and engineering briefs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class ExternalCaseMetadata:
    case_id: str
    source_url: str
    license_name: str
    source_type: str
    independent_reviewer: str
    review_status: str
    notes: str = ""

    def __post_init__(self) -> None:
        parsed = urlparse(self.source_url)
        if not self.case_id or parsed.scheme not in {"http", "https", "doi"}:
            raise ValueError("External cases require an identifier and traceable source URL or DOI")
        if not self.license_name or not self.source_type or not self.independent_reviewer:
            raise ValueError("External cases require license, source type, and independent reviewer")
        if self.review_status not in {"pending", "approved", "rejected"}:
            raise ValueError("review_status must be pending, approved, or rejected")


class ExternalBenchmarkRegistry:
    """Write-once registry for cases that may support external-validity claims."""

    def __init__(self, root: str | Path):
        self._root = Path(root)

    def register(self, metadata: ExternalCaseMetadata, specification: dict) -> Path:
        if metadata.review_status != "approved":
            raise ValueError("Only independently approved external cases may enter the registry")
        destination = self._root / f"{metadata.case_id}.json"
        self._root.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"External case {metadata.case_id} is already registered")
        destination.write_text(json.dumps({"metadata": asdict(metadata), "specification": specification}, indent=2, sort_keys=True) + "\n")
        return destination
