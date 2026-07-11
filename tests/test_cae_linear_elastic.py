import numpy as np
import pytest

from cae.involute import InvoluteGeometry, InvoluteToothSectionFactory
from cae.linear_elastic import PlaneStressMaterial, PlaneStressSolver, TriangularMesh


def _cantilever_mesh() -> TriangularMesh:
    return TriangularMesh(
        nodes_mm=np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 2.0], [0.0, 2.0]]),
        elements=np.array([[0, 1, 2], [0, 2, 3]]),
        thickness_mm=1.0,
    )


def test_plane_stress_solver_returns_finite_cantilever_response() -> None:
    mesh = _cantilever_mesh()
    forces = np.zeros(8)
    forces[2 * 2 + 1] = -100.0
    result = PlaneStressSolver().solve(mesh, PlaneStressMaterial(210_000.0, 0.3), forces, np.array([0, 1, 6, 7]))
    assert result.displacements_mm[2, 1] < 0.0
    assert result.max_von_mises_mpa > 0.0
    assert np.all(np.isfinite(result.element_von_mises_mpa))


def test_solver_rejects_clockwise_triangles() -> None:
    mesh = TriangularMesh(
        nodes_mm=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]),
        elements=np.array([[0, 2, 1]]),
        thickness_mm=1.0,
    )
    with pytest.raises(ValueError, match="counter-clockwise"):
        PlaneStressSolver().solve(mesh, PlaneStressMaterial(1_000.0, 0.3), np.zeros(6), np.array([0, 1, 2, 3]))


def test_involute_geometry_reaches_addendum_circle() -> None:
    module, teeth = 2.0, 24
    flank = InvoluteGeometry.flank(module, teeth)
    assert flank.shape == (24, 2)
    assert np.linalg.norm(flank[-1]) == pytest.approx(InvoluteGeometry.pitch_radius(module, teeth) + module)


@pytest.mark.parametrize("teeth", (18, 24, 44, 48))
def test_tooth_section_preserves_standard_pitch_thickness_in_both_root_regimes(teeth: int) -> None:
    module = 2.0
    section = InvoluteToothSectionFactory().create(module, teeth)
    expected = section.pitch_radius_mm * np.sin(np.pi / (2.0 * teeth))

    assert section.pitch_half_width_mm == pytest.approx(expected)
    assert section.root_width_mm > 0
    assert section.fillet_radius_mm > 0
    assert np.all(np.diff(section.radial_positions_mm) > 0)
