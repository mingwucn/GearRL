"""Governance for externally sourced benchmark cases and engineering briefs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
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
    review_date: str | None = None
    reviewed_specification_sha256: str | None = None

    def __post_init__(self) -> None:
        parsed = urlparse(self.source_url)
        if not self.case_id or parsed.scheme not in {"http", "https", "doi"}:
            raise ValueError("External cases require an identifier and traceable source URL or DOI")
        if not self.license_name or not self.source_type or not self.independent_reviewer:
            raise ValueError("External cases require license, source type, and independent reviewer")
        if self.review_status not in {"pending", "approved", "rejected"}:
            raise ValueError("review_status must be pending, approved, or rejected")
        if self.review_status == "approved":
            try:
                date.fromisoformat(self.review_date or "")
            except ValueError as error:
                raise ValueError("Approved external cases require an ISO review date") from error
            digest = self.reviewed_specification_sha256 or ""
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError("Approved external cases require a canonical specification SHA-256")


class ExternalSpecificationHasher:
    """Canonical identity reviewed by an independent external-case approver."""

    @staticmethod
    def digest(specification: dict) -> str:
        encoded = json.dumps(specification, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return sha256(encoded).hexdigest()


class ExternalBenchmarkRegistry:
    """Write-once registry for cases that may support external-validity claims."""

    def __init__(self, root: str | Path):
        self._root = Path(root)

    def register(self, metadata: ExternalCaseMetadata, specification: dict) -> Path:
        if metadata.review_status != "approved":
            raise ValueError("Only independently approved external cases may enter the registry")
        if ExternalSpecificationHasher.digest(specification) != metadata.reviewed_specification_sha256:
            raise ValueError("External approval is not bound to this specification")
        destination = self._root / f"{metadata.case_id}.json"
        self._root.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"External case {metadata.case_id} is already registered")
        destination.write_text(json.dumps({"metadata": asdict(metadata), "specification": specification}, indent=2, sort_keys=True) + "\n")
        return destination
