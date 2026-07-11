from common.design_models import ValidationCertificate
from rl_agent.certified_reward import CertifiedRewardCalculator


def test_invalid_certificate_cannot_receive_positive_reward() -> None:
    reward = CertifiedRewardCalculator().compute(
        ValidationCertificate(valid=False),
        target_speed_ratio=1.0,
        envelope_area_mm2=100.0,
        reference_area_mm2=100.0,
    )
    assert reward == -100.0


def test_valid_certificate_rewards_compact_safe_design() -> None:
    reward = CertifiedRewardCalculator().compute(
        ValidationCertificate(valid=True, signed_speed_ratio=2.0),
        target_speed_ratio=2.0,
        envelope_area_mm2=80.0,
        reference_area_mm2=100.0,
        safety_factor=2.5,
        minimum_safety_factor=2.0,
    )
    assert reward == 100.0
