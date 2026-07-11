from cae.verification import PlaneStressVerificationSuite


def test_uniform_stress_patch_case_is_reproduced() -> None:
    result = PlaneStressVerificationSuite().patch_test()
    assert result.maximum_relative_error < 1e-10


def test_cantilever_solution_converges_toward_beam_theory() -> None:
    result = PlaneStressVerificationSuite().cantilever_convergence()
    assert result.relative_errors[-1] < result.relative_errors[0]
    assert result.relative_errors[-1] < 0.1


def test_tooth_root_screen_has_independent_analytical_comparator() -> None:
    result = PlaneStressVerificationSuite().gear_root_agreement()
    assert result.finite_element_stress_mpa > 0
    assert result.analytical_stress_mpa > 0
    assert result.gate_passed
    assert result.relative_difference < 0.25
