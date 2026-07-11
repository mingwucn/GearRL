from cae.gear_screening import ToothRootScreeningAnalysis
from common.design_models import GearStage, MaterialLoadCase, Point2D


def _load_case(allowable_stress_mpa: float = 300.0) -> MaterialLoadCase:
    return MaterialLoadCase(
        material_name="steel",
        input_torque_nm=5.0,
        face_width_mm=10.0,
        youngs_modulus_mpa=210_000.0,
        poisson_ratio=0.3,
        allowable_stress_mpa=allowable_stress_mpa,
    )


def test_tooth_screening_returns_physical_loads_and_safety_factor() -> None:
    report = ToothRootScreeningAnalysis().screen(GearStage("input", Point2D(0, 0), (24,), 2.0), 0, _load_case())
    assert report.tangential_force_n > 0
    assert report.radial_force_n > 0
    assert report.max_von_mises_mpa > 0
    assert report.safety_factor > 0
    assert report.mesh_element_count > 2


def test_increasing_allowable_stress_increases_safety_factor() -> None:
    stage = GearStage("input", Point2D(0, 0), (24,), 2.0)
    screening = ToothRootScreeningAnalysis()
    weak = screening.screen(stage, 0, _load_case(150.0))
    strong = screening.screen(stage, 0, _load_case(300.0))
    assert strong.safety_factor == weak.safety_factor * 2.0
