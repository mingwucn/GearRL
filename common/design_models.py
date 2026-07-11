"""Canonical, unit-aware data structures for certified GearRL studies.

These types deliberately live beside the legacy models.  They provide a stable
research interface without silently changing the behaviour of old demos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

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

    def __post_init__(self) -> None:
        if self.min_teeth < 1 or self.max_teeth < self.min_teeth:
            raise ValueError("Invalid tooth-count bounds")
        if self.ratio_tolerance < 0 or self.boundary_clearance < 0:
            raise ValueError("Tolerances and clearances must be non-negative")
        if not 0 < self.pressure_angle_deg < 90:
            raise ValueError("Pressure angle must be between 0 and 90 degrees")


@dataclass(frozen=True)
class MaterialLoadCase:
    material_name: str
    input_torque_nm: float
    face_width_mm: float
    youngs_modulus_mpa: float
    poisson_ratio: float
    allowable_stress_mpa: float
    efficiency: float = 1.0

    def __post_init__(self) -> None:
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


@dataclass
class ValidationCertificate:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    signed_speed_ratio: float | None = None
    minimum_clearance_mm: float | None = None
    cae_reports: list[dict[str, Any]] = field(default_factory=list)
    model_version: str = "certified-planar-v1"

    def to_json(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [asdict(issue) for issue in self.issues],
            "signed_speed_ratio": self.signed_speed_ratio,
            "minimum_clearance_mm": self.minimum_clearance_mm,
            "cae_reports": self.cae_reports,
            "model_version": self.model_version,
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
