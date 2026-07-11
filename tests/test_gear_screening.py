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


def test_production_geometry_depends_on_tooth_count() -> None:
    screening = ToothRootScreeningAnalysis()
    low_count = screening.screen(GearStage("low", Point2D(0, 0), (18,), 2.0), 0, _load_case())
    high_count = screening.screen(GearStage("high", Point2D(0, 0), (40,), 2.0), 0, _load_case())

    assert low_count.model_version == "involute-tooth-root-plane-stress-v3"
    assert low_count.root_width_mm != high_count.root_width_mm
    assert low_count.fillet_radius_mm != high_count.fillet_radius_mm
