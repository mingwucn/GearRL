"""Small, auditable constant-strain-triangle plane-stress solver.

This is intentionally a narrow screening solver, not a replacement for a
contact/fatigue CAE suite.  It owns element assembly and post-processing so
research results remain reproducible from the repository alone.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve


@dataclass(frozen=True)
class PlaneStressMaterial:
    youngs_modulus_mpa: float
    poisson_ratio: float

    def __post_init__(self) -> None:
        if self.youngs_modulus_mpa <= 0:
            raise ValueError("Young's modulus must be positive")
        if not -1.0 < self.poisson_ratio < 0.5:
            raise ValueError("Poisson ratio must be in (-1, 0.5)")

    @property
    def constitutive_matrix(self) -> np.ndarray:
        scale = self.youngs_modulus_mpa / (1.0 - self.poisson_ratio**2)
        return scale * np.array(
            [
                [1.0, self.poisson_ratio, 0.0],
                [self.poisson_ratio, 1.0, 0.0],
                [0.0, 0.0, (1.0 - self.poisson_ratio) / 2.0],
            ],
            dtype=float,
        )


@dataclass(frozen=True)
class TriangularMesh:
    """Two-dimensional mesh using zero-based, counter-clockwise triangles."""

    nodes_mm: np.ndarray
    elements: np.ndarray
    thickness_mm: float

    def __post_init__(self) -> None:
        nodes = np.asarray(self.nodes_mm, dtype=float)
        elements = np.asarray(self.elements, dtype=int)
        if nodes.ndim != 2 or nodes.shape[1] != 2:
            raise ValueError("nodes_mm must have shape (n, 2)")
        if elements.ndim != 2 or elements.shape[1] != 3:
            raise ValueError("elements must have shape (m, 3)")
        if len(nodes) < 3 or len(elements) < 1 or self.thickness_mm <= 0:
            raise ValueError("A non-empty mesh with positive thickness is required")
        if elements.min() < 0 or elements.max() >= len(nodes):
            raise ValueError("Element node index is out of range")
        object.__setattr__(self, "nodes_mm", nodes)
        object.__setattr__(self, "elements", elements)


@dataclass(frozen=True)
class LinearElasticResult:
    displacements_mm: np.ndarray
    element_stresses_mpa: np.ndarray
    element_von_mises_mpa: np.ndarray

    @property
    def max_von_mises_mpa(self) -> float:
        return float(np.max(self.element_von_mises_mpa))


class PlaneStressSolver:
    """Object-oriented entry point for the owned CST plane-stress solver."""

    def solve(
        self,
        mesh: TriangularMesh,
        material: PlaneStressMaterial,
        nodal_forces_n: np.ndarray,
        fixed_dofs: np.ndarray,
    ) -> LinearElasticResult:
        return _solve_plane_stress_kernel(mesh, material, nodal_forces_n, fixed_dofs)


def _solve_plane_stress_kernel(
    mesh: TriangularMesh,
    material: PlaneStressMaterial,
    nodal_forces_n: np.ndarray,
    fixed_dofs: np.ndarray,
) -> LinearElasticResult:
    """Solve a linear, static plane-stress problem using CST elements.

    Parameters use millimetres, Newtons, and MPa.  Since 1 MPa equals
    N/mm^2, no unit conversion is needed inside the stiffness assembly.
    """

    force = np.asarray(nodal_forces_n, dtype=float).reshape(-1)
    dof_count = mesh.nodes_mm.shape[0] * 2
    if force.size != dof_count:
        raise ValueError("nodal_forces_n must contain two values per node")
    fixed = np.unique(np.asarray(fixed_dofs, dtype=int))
    if fixed.size == 0 or fixed.min() < 0 or fixed.max() >= dof_count:
        raise ValueError("fixed_dofs must contain valid constrained degrees of freedom")

    stiffness = np.zeros((dof_count, dof_count), dtype=float)
    element_data: list[tuple[np.ndarray, np.ndarray]] = []
    for element in mesh.elements:
        coords = mesh.nodes_mm[element]
        area, b_matrix = _triangle_kinematics(coords)
        element_stiffness = mesh.thickness_mm * area * b_matrix.T @ material.constitutive_matrix @ b_matrix
        dofs = np.array([2 * node + offset for node in element for offset in (0, 1)], dtype=int)
        stiffness[np.ix_(dofs, dofs)] += element_stiffness
        element_data.append((dofs, b_matrix))

    free = np.setdiff1d(np.arange(dof_count), fixed)
    if not len(free):
        raise ValueError("At least one unconstrained degree of freedom is required")
    free_stiffness = csr_matrix(stiffness[np.ix_(free, free)])
    displacement = np.zeros(dof_count, dtype=float)
    displacement[free] = spsolve(free_stiffness, force[free])
    if not np.all(np.isfinite(displacement)):
        raise ValueError("Singular or ill-conditioned finite-element system")

    stresses = []
    for dofs, b_matrix in element_data:
        stresses.append(material.constitutive_matrix @ b_matrix @ displacement[dofs])
    stress_array = np.asarray(stresses)
    von_mises = np.sqrt(
        stress_array[:, 0] ** 2 - stress_array[:, 0] * stress_array[:, 1] + stress_array[:, 1] ** 2
        + 3.0 * stress_array[:, 2] ** 2
    )
    return LinearElasticResult(displacement.reshape((-1, 2)), stress_array, von_mises)


def _triangle_kinematics(coords: np.ndarray) -> tuple[float, np.ndarray]:
    (x1, y1), (x2, y2), (x3, y3) = coords
    twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if twice_area <= 0:
        raise ValueError("Elements must be counter-clockwise with non-zero area")
    area = twice_area / 2.0
    b1, b2, b3 = y2 - y3, y3 - y1, y1 - y2
    c1, c2, c3 = x3 - x2, x1 - x3, x2 - x1
    b_matrix = np.array(
        [[b1, 0.0, b2, 0.0, b3, 0.0], [0.0, c1, 0.0, c2, 0.0, c3], [c1, b1, c2, b2, c3, b3]],
        dtype=float,
    ) / twice_area
    return area, b_matrix
