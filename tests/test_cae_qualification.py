from cae.qualification import StaticStrengthAdmissionPolicy


def test_unconverged_static_model_fails_admission_qualification() -> None:
    qualification = StaticStrengthAdmissionPolicy().qualification()
    assert qualification.model_version == "involute-tooth-root-plane-stress-v3"
    assert qualification.evidence_id == "cae-refinement-audit-v1"
    assert qualification.qualified is False
    assert "did not converge" in qualification.reason
