"""Published planetary-gear benchmark encoded as an independent digital brief."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import acos, cos, isfinite, pi, sin


@dataclass(frozen=True)
class IntegerRange:
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if self.minimum > self.maximum:
            raise ValueError("Integer range is reversed")

    def contains(self, value: int) -> bool:
        return self.minimum <= value <= self.maximum


@dataclass(frozen=True)
class PublishedPlanetaryGearBrief:
    """Nine-decision planetary benchmark reproduced from a published formulation."""

    case_id: str = "mahdy-2023-planetary-gear-train"
    source_doi: str = "10.1007/s11227-023-05331-y"
    source_url: str = "https://link.springer.com/article/10.1007/s11227-023-05331-y"
    target_ratios: tuple[float, float, float] = (3.11, 1.84, -3.11)
    maximum_diameter_mm: float = 220.0
    planet_choices: tuple[int, ...] = (3, 4, 5)
    module_choices_mm: tuple[float, ...] = (1.75, 2.0, 2.25, 2.5, 2.75, 3.0)
    tooth_ranges: tuple[IntegerRange, ...] = (
        IntegerRange(17, 96),
        IntegerRange(14, 54),
        IntegerRange(14, 51),
        IntegerRange(17, 46),
        IntegerRange(14, 51),
        IntegerRange(48, 124),
    )

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlanetaryGearCandidate:
    z1: int
    z2: int
    z3: int
    z4: int
    z5: int
    z6: int
    planet_count: int
    module_1_mm: float
    module_2_mm: float

    @property
    def teeth(self) -> tuple[int, ...]:
        return self.z1, self.z2, self.z3, self.z4, self.z5, self.z6

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PlanetaryGearEvaluation:
    objective: float
    ratios: tuple[float, float, float]
    inequality_values: tuple[float, ...]
    assembly_remainder: int
    valid: bool
    issue_codes: tuple[str, ...]

    def to_json(self) -> dict:
        return asdict(self)


class PublishedPlanetaryGearEvaluator:
    """Evaluate the published objective and its ten inequalities plus assembly rule."""

    MODEL_VERSION = "mahdy-planetary-formulation-v1"

    def evaluate(self, brief: PublishedPlanetaryGearBrief, candidate: PlanetaryGearCandidate) -> PlanetaryGearEvaluation:
        issues = list(self._domain_issues(brief, candidate))
        if issues:
            return PlanetaryGearEvaluation(float("inf"), (float("nan"),) * 3, (), -1, False, tuple(issues))
        z1, z2, z3, z4, z5, z6 = candidate.teeth
        p, m1, m2 = candidate.planet_count, candidate.module_1_mm, candidate.module_2_mm
        ratio_1 = z6 / z4
        ratio_2 = z6 * (z1 * z3 + z2 * z4) / (z1 * z3 * (z6 - z4))
        ratio_reverse = -(z2 * z6) / (z1 * z3)
        ratios = ratio_1, ratio_2, ratio_reverse
        objective = max(abs(value - target) for value, target in zip(ratios, brief.target_ratios, strict=True))
        denominator = 2.0 * (z6 - z3) * (z4 + z5)
        cosine = ((z4 + z5) ** 2 + (z6 - z3) ** 2 - (z3 + z5) ** 2) / denominator
        if not -1.0 <= cosine <= 1.0:
            return PlanetaryGearEvaluation(objective, ratios, (), (z6 - z4) % p, False, ("invalid_beta_geometry",))
        beta = acos(cosine)
        delta = 0.5
        inequalities = (
            m2 * (z6 + 2.5) - brief.maximum_diameter_mm,
            m1 * (z1 + z2) + m1 * (z2 + 2) - brief.maximum_diameter_mm,
            m2 * (z4 + z5) + m2 * (z5 + 2) - brief.maximum_diameter_mm,
            abs(m1 * (z1 + z2) - m2 * (z6 - z3)) - m1 - m2,
            -(z1 + z2) * sin(pi / p) + z2 + 2 + delta,
            -(z6 - z3) * sin(pi / p) + z3 + 2 + delta,
            -(z4 + z5) * sin(pi / p) + z5 + 2 + delta,
            (z3 + z5 + 2 + delta) ** 2
            - (z6 - z3) ** 2
            - (z4 + z5) ** 2
            + 2 * (z6 - z3) * (z4 + z5) * cos(2 * pi / p - beta),
            z4 - z6 + 2 * z5 + 2 * delta + 4,
            2 * z3 - z6 + z4 + 2 * delta + 4,
        )
        violated = tuple(f"g{index}" for index, value in enumerate(inequalities, 1) if value > 1e-12)
        remainder = (z6 - z4) % p
        if remainder:
            violated = (*violated, "h1_assembly_divisibility")
        return PlanetaryGearEvaluation(objective, ratios, inequalities, remainder, not violated, violated)

    @staticmethod
    def _domain_issues(brief: PublishedPlanetaryGearBrief, candidate: PlanetaryGearCandidate) -> tuple[str, ...]:
        issues = []
        if any(type(value) is not int for value in candidate.teeth):
            issues.append("non_integer_teeth")
        elif any(not bounds.contains(value) for bounds, value in zip(brief.tooth_ranges, candidate.teeth, strict=True)):
            issues.append("tooth_bound")
        if candidate.planet_count not in brief.planet_choices:
            issues.append("planet_count_choice")
        if candidate.module_1_mm not in brief.module_choices_mm or candidate.module_2_mm not in brief.module_choices_mm:
            issues.append("module_choice")
        if any(not isfinite(value) for value in (*candidate.teeth, candidate.planet_count, candidate.module_1_mm, candidate.module_2_mm)):
            issues.append("non_finite_decision")
        return tuple(issues)
