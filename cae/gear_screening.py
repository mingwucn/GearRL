"""Conservative, self-developed static tooth-root screening for spur gears.

The model is a two-dimensional plane-stress approximation of the critical tooth
section.  It is suitable for candidate filtering and reports its assumptions;
it is not a replacement for contact, fatigue, or full gearbox CAE.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import radians, tan

import numpy as np

from cae.linear_elastic import PlaneStressMaterial, PlaneStressSolver, TriangularMesh
from cae.involute import InvoluteToothSectionFactory, ToothSectionGeometry
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
    tooth_count: int
    pressure_angle_deg: float
    root_width_mm: float
    section_height_mm: float
    fillet_radius_mm: float
    transmitted_torque_nm: float
    model_version: str = "involute-tooth-root-plane-stress-v3"

    def to_json(self) -> dict[str, float | int | str]:
        return {
            "stage_id": self.stage_id,
            "member": self.member,
            "tangential_force_n": self.tangential_force_n,
            "radial_force_n": self.radial_force_n,
            "max_von_mises_mpa": self.max_von_mises_mpa,
            "safety_factor": self.safety_factor,
            "mesh_element_count": self.mesh_element_count,
            "tooth_count": self.tooth_count,
            "pressure_angle_deg": self.pressure_angle_deg,
            "root_width_mm": self.root_width_mm,
            "section_height_mm": self.section_height_mm,
            "fillet_radius_mm": self.fillet_radius_mm,
            "transmitted_torque_nm": self.transmitted_torque_nm,
            "model_version": self.model_version,
        }


class ToothRootScreeningAnalysis:
    """Conservative CAE service for one gear-member tooth-root screen."""

    def __init__(self, solver: PlaneStressSolver | None = None, mesh_factory: "ToothRootMeshFactory | None" = None):
        self._solver = solver or PlaneStressSolver()
        self._mesh_factory = mesh_factory or ToothRootMeshFactory()

    def screen(
        self,
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
        mesh, geometry = self._mesh_factory.create_with_geometry(
            stage.module_mm,
            stage.teeth[member],
            load_case.face_width_mm,
            pressure_angle_deg,
        )
        forces = np.zeros(mesh.nodes_mm.shape[0] * 2)
        top = np.flatnonzero(np.isclose(mesh.nodes_mm[:, 1], np.max(mesh.nodes_mm[:, 1])))
        weights = np.ones(len(top))
        weights[[0, -1]] = 0.5
        weights /= weights.sum()
        # The local tooth axis is radial (+y): tangential load bends the tooth
        # in x, while the radial component acts along the tooth axis.
        forces[2 * top] = -tangential_force * weights
        forces[2 * top + 1] = -radial_force * weights
        base = np.flatnonzero(np.isclose(mesh.nodes_mm[:, 1], 0.0))
        result = self._solver.solve(
            mesh,
            PlaneStressMaterial(load_case.youngs_modulus_mpa, load_case.poisson_ratio),
            forces,
            fixed_dofs=np.concatenate((2 * base, 2 * base + 1)),
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
            tooth_count=stage.teeth[member],
            pressure_angle_deg=pressure_angle_deg,
            root_width_mm=geometry.root_width_mm,
            section_height_mm=geometry.height_mm,
            fillet_radius_mm=geometry.fillet_radius_mm,
            transmitted_torque_nm=torque_nm,
        )
class ToothRootMeshFactory:
    """Create a structured mesh conforming to a sampled involute tooth section."""

    def __init__(
        self,
        divisions_x: int = 8,
        divisions_y: int = 12,
        geometry_factory: InvoluteToothSectionFactory | None = None,
        foundation_depth_modules: float = 1.0,
    ):
        if min(divisions_x, divisions_y) < 1 or foundation_depth_modules <= 0:
            raise ValueError("Tooth mesh divisions must be positive")
        self._divisions_x = divisions_x
        self._divisions_y = divisions_y
        self._geometry_factory = geometry_factory or InvoluteToothSectionFactory()
        self._foundation_depth_modules = foundation_depth_modules

    def create(
        self,
        module_mm: float,
        teeth: int,
        face_width_mm: float,
        pressure_angle_deg: float = 20.0,
    ) -> TriangularMesh:
        return self.create_with_geometry(module_mm, teeth, face_width_mm, pressure_angle_deg)[0]

    def create_with_geometry(
        self,
        module_mm: float,
        teeth: int,
        face_width_mm: float,
        pressure_angle_deg: float = 20.0,
    ) -> tuple[TriangularMesh, ToothSectionGeometry]:
        if module_mm <= 0 or teeth <= 0 or face_width_mm <= 0:
            raise ValueError("Gear dimensions must be positive")
        geometry = self._geometry_factory.create(module_mm, teeth, pressure_angle_deg)
        foundation_depth = self._foundation_depth_modules * module_mm
        foundation_divisions = max(2, self._divisions_y // 4)
        nodes = []
        root_half_width = geometry.root_width_mm / 2.0
        for iy in range(foundation_divisions + 1):
            radial_position = foundation_depth * iy / foundation_divisions
            nodes.extend(
                (-root_half_width + 2.0 * root_half_width * ix / self._divisions_x, radial_position)
                for ix in range(self._divisions_x + 1)
            )
        for iy in range(1, self._divisions_y + 1):
            fraction = iy / self._divisions_y
            tooth_position = geometry.height_mm * fraction
            radial_position = foundation_depth + tooth_position
            half_width = geometry.half_width(tooth_position)
            nodes.extend(
                (-half_width + 2.0 * half_width * ix / self._divisions_x, radial_position)
                for ix in range(self._divisions_x + 1)
            )
        elements = []
        row = self._divisions_x + 1
        total_rows = foundation_divisions + self._divisions_y
        for iy in range(total_rows):
            for ix in range(self._divisions_x):
                lower_left = iy * row + ix
                lower_right = lower_left + 1
                upper_left = lower_left + row
                upper_right = upper_left + 1
                elements.extend(((lower_left, lower_right, upper_right), (lower_left, upper_right, upper_left)))
        return TriangularMesh(np.asarray(nodes), np.asarray(elements), face_width_mm), geometry
