"""Reward shaping that consumes independent validation certificates only."""

from __future__ import annotations

from common.design_models import ValidationCertificate


class CertifiedRewardCalculator:
    """Reward service that accepts independent certificates only."""

    def compute(
        self,
        certificate: ValidationCertificate,
        *,
        target_speed_ratio: float | None,
        envelope_area_mm2: float,
        reference_area_mm2: float,
        safety_factor: float | None = None,
        minimum_safety_factor: float | None = None,
    ) -> float:
        """Return a bounded reward without rewarding an invalid design.

    The verifier is the single source of truth.  Area and CAE terms are only
    evaluated after geometric and kinematic validity has been established.
    """

        if not certificate.valid:
            return -100.0
        if envelope_area_mm2 <= 0 or reference_area_mm2 <= 0:
            raise ValueError("Areas must be positive")
        ratio_score = 1.0
        if target_speed_ratio is not None:
            if certificate.signed_speed_ratio is None:
                return -100.0
            ratio_score = 1.0 / (1.0 + abs(certificate.signed_speed_ratio - target_speed_ratio))
        compactness_score = min(1.0, reference_area_mm2 / envelope_area_mm2)
        safety_score = 1.0
        if minimum_safety_factor is not None:
            if safety_factor is None or safety_factor < minimum_safety_factor:
                return -100.0
            safety_score = min(1.0, safety_factor / minimum_safety_factor)
        return 60.0 * ratio_score + 25.0 * compactness_score + 15.0 * safety_score
