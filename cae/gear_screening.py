"""Conservative, self-developed static tooth-root screening for spur gears.

The model is a two-dimensional plane-stress approximation of the critical tooth
section.  It is suitable for candidate filtering and reports its assumptions;
it is not a replacement for contact, fatigue, or full gearbox CAE.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, radians, tan

import numpy as np

from cae.linear_elastic import PlaneStressMaterial, TriangularMesh, solve_plane_stress
from common.design_models import GearStage, MaterialLoadCase


@dataclass(frozen=True)
class ToothScreeningReport:
    stage_id: str
    member: int
    tangential_force_n: float
    radial_force_n: float
    max_von_mises_mpa: float
    safety_factor: float
    mesh_element_count: int
    model_version: str = "tooth-root-plane-stress-v1"

    def to_json(self) -> dict[str, float | int | str]:
        return {
            "stage_id": self.stage_id,
            "member": self.member,
            "tangential_force_n": self.tangential_force_n,
            "radial_force_n": self.radial_force_n,
            "max_von_mises_mpa": self.max_von_mises_mpa,
            "safety_factor": self.safety_factor,
            "mesh_element_count": self.mesh_element_count,
            "model_version": self.model_version,
        }


def screen_tooth_root(
    stage: GearStage,
    member: int,
    load_case: MaterialLoadCase,
    transmitted_torque_nm: float | None = None,
    pressure_angle_deg: float = 20.0,
) -> ToothScreeningReport:
    """Screen a tooth root using a conservative plane-stress finite-element mesh."""

    if member < 0 or member >= len(stage.teeth):
        raise IndexError("Invalid gear member")
    torque_nm = transmitted_torque_nm if transmitted_torque_nm is not None else load_case.input_torque_nm
    if torque_nm <= 0:
        raise ValueError("Transmitted torque must be positive")
    pitch_radius = stage.pitch_radius_mm(member)
    tangential_force = torque_nm * 1_000.0 / pitch_radius
    radial_force = tangential_force * tan(radians(pressure_angle_deg))
    mesh = _tooth_root_mesh(stage.module_mm, stage.teeth[member], load_case.face_width_mm)
    forces = np.zeros(mesh.nodes_mm.shape[0] * 2)
    # Two top nodes share tangential and radial load at the critical contact zone.
    for node in (2, 3):
        forces[2 * node] = -radial_force / 2.0
        forces[2 * node + 1] = -tangential_force / 2.0
    result = solve_plane_stress(
        mesh,
        PlaneStressMaterial(load_case.youngs_modulus_mpa, load_case.poisson_ratio),
        forces,
        fixed_dofs=np.array([0, 1, 2, 3]),
    )
    maximum = result.max_von_mises_mpa
    safety = load_case.allowable_stress_mpa / maximum if maximum > 0 else float("inf")
    return ToothScreeningReport(
        stage_id=stage.id,
        member=member,
        tangential_force_n=tangential_force,
        radial_force_n=radial_force,
        max_von_mises_mpa=maximum,
        safety_factor=safety,
        mesh_element_count=len(mesh.elements),
    )


def _tooth_root_mesh(module_mm: float, teeth: int, face_width_mm: float) -> TriangularMesh:
    """Create a reproducible critical-section mesh from standard tooth dimensions."""
    circular_pitch = pi * module_mm
    root_half_width = circular_pitch * 0.50
    tip_half_width = circular_pitch * 0.25
    # Full-depth tooth from dedendum circle to addendum circle: 2.25 module.
    height = 2.25 * module_mm
    nodes = np.array(
        [
            [-root_half_width, 0.0],
            [root_half_width, 0.0],
            [tip_half_width, height],
            [-tip_half_width, height],
        ]
    )
    return TriangularMesh(nodes, np.array([[0, 1, 2], [0, 2, 3]]), face_width_mm)
