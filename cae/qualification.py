"""Qualification policy for using digital stress models as admission gates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StaticStrengthAdmissionQualification:
    model_version: str
    qualified: bool
    evidence_id: str
    reason: str


class StaticStrengthAdmissionPolicy:
    """Fail closed until convergence and independent-reference gates pass."""

    CURRENT = StaticStrengthAdmissionQualification(
        model_version="involute-tooth-root-plane-stress-v3",
        qualified=False,
        evidence_id="cae-refinement-audit-v1",
        reason="Peak root stress did not converge under extended mesh refinement",
    )

    def qualification(self) -> StaticStrengthAdmissionQualification:
        return self.CURRENT
