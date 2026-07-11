"""Canonical, unit-aware data structures for certified GearRL studies.

These types deliberately live beside the legacy models.  They provide a stable
research interface without silently changing the behaviour of old demos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from copy import deepcopy
from math import isfinite
from typing import Any, Mapping, Sequence


class CanonicalNumericGuard:
    """Central finite-number invariant for certificate-bearing domain objects."""

    @staticmethod
    def require_finite(**values: float | None) -> None:
        invalid = [name for name, value in values.items() if value is not None and not isfinite(value)]
        if invalid:
            raise ValueError(f"Non-finite canonical values: {', '.join(sorted(invalid))}")


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def __post_init__(self) -> None:
        CanonicalNumericGuard.require_finite(x=self.x, y=self.y)

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "Point2D":
        return cls(float(value["x"]), float(value["y"]))

    def to_json(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class DesignConstraints:
    """Hard constraints for a planar external-spur gear train.

    ``target_speed_ratio`` is omega_out / omega_in.  A negative value denotes
    a reversal of rotation direction.  ``None`` leaves the ratio unconstrained.
    """

    target_speed_ratio: float | None
    ratio_tolerance: float = 1e-6
    boundary_clearance: float = 0.0
    min_teeth: int = 17
    max_teeth: int = 200
    pressure_angle_deg: float = 20.0
    min_safety_factor: float | None = None
    transverse_backlash_allowance_mm: float = 0.0

    def __post_init__(self) -> None:
        CanonicalNumericGuard.require_finite(
            target_speed_ratio=self.target_speed_ratio,
            ratio_tolerance=self.ratio_tolerance,
            boundary_clearance=self.boundary_clearance,
            pressure_angle_deg=self.pressure_angle_deg,
            min_safety_factor=self.min_safety_factor,
            transverse_backlash_allowance_mm=self.transverse_backlash_allowance_mm,
        )
        if self.min_teeth < 1 or self.max_teeth < self.min_teeth:
            raise ValueError("Invalid tooth-count bounds")
        if self.ratio_tolerance < 0:
            raise ValueError("ratio_tolerance must be non-negative")
        if self.boundary_clearance < 0:
            raise ValueError("boundary_clearance must be non-negative")
        if self.transverse_backlash_allowance_mm < 0:
            raise ValueError("transverse_backlash_allowance_mm must be non-negative")
        if not 0 < self.pressure_angle_deg < 90:
            raise ValueError("Pressure angle must be between 0 and 90 degrees")


@dataclass(frozen=True)
class MaterialLoadCase:
    """Static load/material declaration with per-mesh power efficiency."""

    material_name: str
    input_torque_nm: float
    face_width_mm: float
    youngs_modulus_mpa: float
    poisson_ratio: float
    allowable_stress_mpa: float
    efficiency: float = 1.0

    def __post_init__(self) -> None:
        CanonicalNumericGuard.require_finite(
            input_torque_nm=self.input_torque_nm,
            face_width_mm=self.face_width_mm,
            youngs_modulus_mpa=self.youngs_modulus_mpa,
            poisson_ratio=self.poisson_ratio,
            allowable_stress_mpa=self.allowable_stress_mpa,
            efficiency=self.efficiency,
        )
        if self.input_torque_nm <= 0 or self.face_width_mm <= 0:
            raise ValueError("Torque and face width must be positive")
        if self.youngs_modulus_mpa <= 0 or self.allowable_stress_mpa <= 0:
            raise ValueError("Material stiffness and allowable stress must be positive")
        if not 0 < self.efficiency <= 1:
            raise ValueError("Efficiency must be in (0, 1]")


@dataclass(frozen=True)
class GearStage:
    """One shaft carrying one simple gear or an ordered compound gear set."""

    id: str
    center: Point2D
    teeth: tuple[int, ...]
    module_mm: float
    axial_layers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        CanonicalNumericGuard.require_finite(module_mm=self.module_mm)
        if not self.id or not self.teeth:
            raise ValueError("A gear stage requires an id and at least one member")
        if self.module_mm <= 0 or any(teeth <= 0 for teeth in self.teeth):
            raise ValueError("Gear module and tooth counts must be positive")
        if self.axial_layers and len(self.axial_layers) != len(self.teeth):
            raise ValueError("axial_layers must match the number of gear members")

    def pitch_radius_mm(self, member: int) -> float:
        return self.module_mm * self.teeth[member] / 2.0

    def outer_radius_mm(self) -> float:
        # Standard full-depth external spur gear addendum equals one module.
        return max(self.module_mm * (teeth + 2) / 2.0 for teeth in self.teeth)

    def layer(self, member: int) -> int:
        return self.axial_layers[member] if self.axial_layers else member


@dataclass(frozen=True)
class MeshEdge:
    """An external mesh from a driving stage member to a driven member."""

    driver_stage_id: str
    driver_member: int
    driven_stage_id: str
    driven_member: int
    center_distance_tolerance_mm: float = 1e-6

    def __post_init__(self) -> None:
        CanonicalNumericGuard.require_finite(center_distance_tolerance_mm=self.center_distance_tolerance_mm)
        if self.driver_stage_id == self.driven_stage_id:
            raise ValueError("A mesh must connect distinct shafts")
        if min(self.driver_member, self.driven_member) < 0:
            raise ValueError("Gear-member indices must be non-negative")
        if self.center_distance_tolerance_mm < 0:
            raise ValueError("Center-distance tolerance must be non-negative")


@dataclass(frozen=True)
class DesignProblem:
    boundary: tuple[Point2D, ...]
    input_stage_id: str
    output_stage_id: str
    constraints: DesignConstraints
    load_case: MaterialLoadCase | None = None
    units: str = "mm"

    def __post_init__(self) -> None:
        if len(self.boundary) < 3:
            raise ValueError("A boundary requires at least three points")
        if not self.input_stage_id or not self.output_stage_id:
            raise ValueError("Input and output stage ids are required")
        if self.input_stage_id == self.output_stage_id:
            raise ValueError("Input and output stages must differ")
        if self.units != "mm":
            raise ValueError("The certified planar model uses millimetres")


@dataclass(frozen=True)
class GearTrain:
    stages: tuple[GearStage, ...]
    meshes: tuple[MeshEdge, ...]

    def __post_init__(self) -> None:
        ids = [stage.id for stage in self.stages]
        if not self.stages or len(ids) != len(set(ids)):
            raise ValueError("Gear stages must have unique ids")

    def stage_map(self) -> dict[str, GearStage]:
        return {stage.id: stage for stage in self.stages}

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class CertificateModelIdentity:
    planar_model: str = "certified-planar-v3"
    specification_model: str | None = None
    static_strength_model: str | None = None
    strength_qualification_evidence: str | None = None

    def to_json(self) -> dict[str, str | None]:
        return asdict(self)


class ImmutableReport(Mapping[str, Any]):
    """Read-only report mapping that serializes through ``dataclasses.asdict``."""

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = deepcopy(dict(values))

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __deepcopy__(self, memo):
        return deepcopy(self._values, memo)


@dataclass(frozen=True)
class ValidationCertificate:
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()
    signed_speed_ratio: float | None = None
    minimum_clearance_mm: float | None = None
    cae_reports: tuple[Mapping[str, Any], ...] = ()
    model_identity: CertificateModelIdentity = field(default_factory=CertificateModelIdentity)

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "cae_reports", tuple(ImmutableReport(report) for report in self.cae_reports))

    @property
    def model_version(self) -> str:
        """Compatibility label; component identities are authoritative."""
        return self.model_identity.planar_model

    def to_json(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [asdict(issue) for issue in self.issues],
            "signed_speed_ratio": self.signed_speed_ratio,
            "minimum_clearance_mm": self.minimum_clearance_mm,
            "cae_reports": [dict(report) for report in self.cae_reports],
            "model_version": self.model_version,
            "model_identity": self.model_identity.to_json(),
        }


@dataclass(frozen=True)
class ManufacturingArtifact:
    """Traceable concept-manufacturing export bound to a validation certificate."""

    artifact_id: str
    svg_path: str
    dxf_path: str
    certificate: dict[str, Any]
    step_path: str | None = None
    physical_validation_complete: bool = False

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
