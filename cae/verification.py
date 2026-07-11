"""Independent numerical verification cases for the owned plane-stress solver."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cae.gear_screening import ToothRootScreeningAnalysis
from cae.linear_elastic import PlaneStressMaterial, PlaneStressSolver, TriangularMesh
from common.design_models import GearStage, MaterialLoadCase, Point2D


class RectangularMeshFactory:
    """Create deterministic structured triangular meshes for verification cases."""

    def create(self, length_mm: float, height_mm: float, nx: int, ny: int, thickness_mm: float) -> TriangularMesh:
        if min(length_mm, height_mm, thickness_mm) <= 0 or min(nx, ny) < 1:
            raise ValueError("Rectangle dimensions and mesh divisions must be positive")
        nodes = np.array([(length_mm * ix / nx, height_mm * iy / ny) for iy in range(ny + 1) for ix in range(nx + 1)])
        elements = []
        width = nx + 1
        for iy in range(ny):
            for ix in range(nx):
                lower_left = iy * width + ix
                lower_right = lower_left + 1
                upper_left = lower_left + width
                upper_right = upper_left + 1
                elements.extend(((lower_left, lower_right, upper_right), (lower_left, upper_right, upper_left)))
        return TriangularMesh(nodes, np.asarray(elements), thickness_mm)


@dataclass(frozen=True)
class PatchTestResult:
    expected_stress_mpa: float
    maximum_relative_error: float


@dataclass(frozen=True)
class CantileverConvergenceResult:
    element_counts: tuple[int, ...]
    tip_displacements_mm: tuple[float, ...]
    analytical_displacement_mm: float
    relative_errors: tuple[float, ...]


@dataclass(frozen=True)
class GearRootAgreementResult:
    finite_element_stress_mpa: float
    analytical_stress_mpa: float
    relative_difference: float
    agreement_limit: float
    gate_passed: bool


class PlaneStressVerificationSuite:
    """Execute patch, analytical, convergence, and gear-root agreement checks."""

    def __init__(self, solver: PlaneStressSolver | None = None, meshes: RectangularMeshFactory | None = None):
        self._solver = solver or PlaneStressSolver()
        self._meshes = meshes or RectangularMeshFactory()

    def patch_test(self) -> PatchTestResult:
        mesh = self._meshes.create(10.0, 2.0, 4, 2, 1.0)
        expected = 10.0
        forces = np.zeros(len(mesh.nodes_mm) * 2)
        right = np.flatnonzero(np.isclose(mesh.nodes_mm[:, 0], 10.0))
        right = right[np.argsort(mesh.nodes_mm[right, 1])]
        weights = np.ones(len(right))
        weights[[0, -1]] = 0.5
        forces[2 * right] = expected * mesh.thickness_mm * 2.0 * weights / weights.sum()
        left = np.flatnonzero(np.isclose(mesh.nodes_mm[:, 0], 0.0))
        fixed = np.concatenate((2 * left, np.array([2 * left[0] + 1])))
        result = self._solver.solve(mesh, PlaneStressMaterial(210_000.0, 0.3), forces, fixed)
        error = float(np.max(np.abs(result.element_stresses_mpa[:, 0] - expected)) / expected)
        return PatchTestResult(expected, error)

    def cantilever_convergence(self, divisions: tuple[int, ...] = (10, 20, 40)) -> CantileverConvergenceResult:
        length, height, thickness, load, youngs = 10.0, 2.0, 1.0, -100.0, 210_000.0
        analytical = load * length**3 / (3.0 * youngs * (thickness * height**3 / 12.0))
        displacements, counts = [], []
        for nx in divisions:
            ny = max(2, nx // 5)
            mesh = self._meshes.create(length, height, nx, ny, thickness)
            forces = np.zeros(len(mesh.nodes_mm) * 2)
            right = np.flatnonzero(np.isclose(mesh.nodes_mm[:, 0], length))
            forces[2 * right + 1] = load / len(right)
            left = np.flatnonzero(np.isclose(mesh.nodes_mm[:, 0], 0.0))
            fixed = np.concatenate((2 * left, 2 * left + 1))
            result = self._solver.solve(mesh, PlaneStressMaterial(youngs, 0.3), forces, fixed)
            displacements.append(float(np.mean(result.displacements_mm[right, 1])))
            counts.append(len(mesh.elements))
        errors = tuple(abs(value - analytical) / abs(analytical) for value in displacements)
        return CantileverConvergenceResult(tuple(counts), tuple(displacements), analytical, errors)

    def gear_root_agreement(self, agreement_limit: float = 0.25) -> GearRootAgreementResult:
        module, teeth, face_width, torque = 2.0, 24, 10.0, 5.0
        stage = GearStage("verification", Point2D(0.0, 0.0), (teeth,), module)
        load = MaterialLoadCase("steel", torque, face_width, 210_000.0, 0.3, 800.0)
        report = ToothRootScreeningAnalysis(self._solver).screen(stage, 0, load)
        tangential_force = torque * 1_000.0 / stage.pitch_radius_mm(0)
        root_width = np.pi * module
        height = 2.25 * module
        analytical = 6.0 * tangential_force * height / (face_width * root_width**2)
        difference = abs(report.max_von_mises_mpa - analytical) / analytical
        return GearRootAgreementResult(report.max_von_mises_mpa, analytical, difference, agreement_limit, difference <= agreement_limit)
