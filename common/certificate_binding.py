"""Canonical subject binding for independently verifiable certificates."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass, replace
from hashlib import sha256
import json
from typing import Any

from common.design_models import CertificateSubjectIdentity, ValidationCertificate


class CanonicalSubjectHasher:
    """Hash domain objects through deterministic JSON serialization."""

    @classmethod
    def digest(cls, value: Any) -> str:
        payload = value.to_json() if hasattr(value, "to_json") else asdict(value) if is_dataclass(value) else value
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(encoded).hexdigest()


class ValidationCertificateBinder:
    """Bind and verify certificates against the precise problem and train."""

    def bind(
        self,
        certificate: ValidationCertificate,
        problem: Any,
        train: Any,
        *,
        subject_schema: str,
        verifier_identity: str,
    ) -> ValidationCertificate:
        identity = CertificateSubjectIdentity(
            subject_schema=subject_schema,
            problem_sha256=CanonicalSubjectHasher.digest(problem),
            train_sha256=CanonicalSubjectHasher.digest(train),
            verifier_identity=verifier_identity,
        )
        return replace(certificate, subject_identity=identity)

    def matches(
        self,
        certificate: ValidationCertificate,
        problem: Any,
        train: Any,
        *,
        subject_schema: str,
        verifier_identity: str,
    ) -> bool:
        identity = certificate.subject_identity
        return identity is not None and (
            identity.subject_schema == subject_schema
            and identity.verifier_identity == verifier_identity
            and identity.problem_sha256 == CanonicalSubjectHasher.digest(problem)
            and identity.train_sha256 == CanonicalSubjectHasher.digest(train)
        )
