"""Traceable material and operating envelopes for digital CAE screening."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from statistics import median

from benchmark.generator import BenchmarkInstance
from common.design_models import MaterialLoadCase
from evaluation.cae_study import CAEStudyOutcome, StratifiedCAEStudy


@dataclass(frozen=True)
class TraceableMaterial:
    """A sourced yield datum and its explicitly derived static allowable."""

    grade: str
    product_form: str
    thickness_scope_mm: str
    minimum_yield_strength_mpa: float
    youngs_modulus_mpa: float
    poisson_ratio: float
    static_screen_factor: float
    source_title: str
    source_url: str
    source_scope: str

    def __post_init__(self) -> None:
        if self.minimum_yield_strength_mpa <= 0 or self.youngs_modulus_mpa <= 0:
            raise ValueError("Material strengths and stiffness must be positive")
        if not 0 < self.poisson_ratio < 0.5 or self.static_screen_factor <= 1:
            raise ValueError("Invalid elastic constants or static screening factor")
        if not self.source_url.startswith("https://"):
            raise ValueError("A traceable HTTPS source is required")

    @property
    def static_allowable_stress_mpa(self) -> float:
        return self.minimum_yield_strength_mpa / self.static_screen_factor

    def load_case(self, torque_nm: float, face_width_mm: float, efficiency: float) -> MaterialLoadCase:
        return MaterialLoadCase(
            material_name=f"{self.grade} ({self.product_form})",
            input_torque_nm=torque_nm,
            face_width_mm=face_width_mm,
            youngs_modulus_mpa=self.youngs_modulus_mpa,
            poisson_ratio=self.poisson_ratio,
            allowable_stress_mpa=self.static_allowable_stress_mpa,
            efficiency=efficiency,
        )


@dataclass(frozen=True)
class LoadEnvelopeCase:
    case_id: str
    material: TraceableMaterial
    torque_nm: float
    face_width_mm: float
    efficiency: float

    @property
    def load_case(self) -> MaterialLoadCase:
        return self.material.load_case(self.torque_nm, self.face_width_mm, self.efficiency)


class AEIStaticEnvelopeCatalog:
    """Build the frozen, fully digital AEI screening envelope."""

    @staticmethod
    def materials() -> tuple[TraceableMaterial, ...]:
        return (
            TraceableMaterial(
                grade="S355",
                product_form="plate",
                thickness_scope_mm="5-16",
                minimum_yield_strength_mpa=355.0,
                youngs_modulus_mpa=210_000.0,
                poisson_ratio=0.3,
                static_screen_factor=1.5,
                source_title="ArcelorMittal Constructalia: S355 structural steel grades",
                source_url="https://constructalia.arcelormittal.com/en/steel-grades/s355",
                source_scope="Minimum transverse yield strength for 5-16 mm product thickness.",
            ),
            TraceableMaterial(
                grade="Toolox 44",
                product_form="plate",
                thickness_scope_mm="6-130",
                minimum_yield_strength_mpa=1150.0,
                youngs_modulus_mpa=205_000.0,
                poisson_ratio=0.3,
                static_screen_factor=1.5,
                source_title="SSAB: Toolox 44 product data",
                source_url="https://www.ssab.com/en-gb/brands-and-products/toolox/product-offer/toolox-44",
                source_scope="Guaranteed minimum 0.2% proof strength for plate, 6-130 mm.",
            ),
        )

    def cases(self) -> tuple[LoadEnvelopeCase, ...]:
        cases = []
        for material, torque, width, efficiency in product(
            self.materials(), (1.0, 3.0), (8.0, 12.0), (0.95, 0.98)
        ):
            slug = material.grade.lower().replace(" ", "-")
            case_id = f"{slug}-t{torque:g}-w{width:g}-e{efficiency:.2f}"
            cases.append(LoadEnvelopeCase(case_id, material, torque, width, efficiency))
        return tuple(cases)


@dataclass(frozen=True)
class LoadEnvelopeOutcome:
    case_id: str
    material: dict
    load_case: dict
    layout_outcomes: tuple[CAEStudyOutcome, ...]
    valid_fraction: float
    minimum_safety_factor: float
    median_safety_factor: float


class LoadEnvelopeStudy:
    """Evaluate every declared envelope case on the same stratified layouts."""

    def __init__(self, minimum_safety_factor: float = 1.0):
        if minimum_safety_factor <= 0:
            raise ValueError("Minimum safety factor must be positive")
        self._minimum_safety_factor = minimum_safety_factor

    def evaluate(
        self, instances: list[BenchmarkInstance], cases: tuple[LoadEnvelopeCase, ...], sample_size: int
    ) -> tuple[LoadEnvelopeOutcome, ...]:
        results = []
        for case in cases:
            layouts = tuple(
                StratifiedCAEStudy(case.load_case, self._minimum_safety_factor).evaluate(instances, sample_size)
            )
            safety = sorted(item.minimum_safety_factor for item in layouts if item.minimum_safety_factor is not None)
            if not safety:
                raise ValueError(f"Envelope case produced no CAE reports: {case.case_id}")
            results.append(
                LoadEnvelopeOutcome(
                    case_id=case.case_id,
                    material=asdict(case.material),
                    load_case=asdict(case.load_case),
                    layout_outcomes=layouts,
                    valid_fraction=sum(item.valid for item in layouts) / len(layouts),
                    minimum_safety_factor=safety[0],
                    median_safety_factor=median(safety),
                )
            )
        return tuple(results)
