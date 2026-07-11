import numpy as np

from cae.gmsh_mesher import GmshMesher


def test_gmsh_mesher_returns_counter_clockwise_triangles() -> None:
    mesh = GmshMesher().mesh([(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)], 2.0, 2.0)
    assert len(mesh.elements) > 0
    for element in mesh.elements:
        points = mesh.nodes_mm[element]
        twice_area = (points[1, 0] - points[0, 0]) * (points[2, 1] - points[0, 1]) - (
            points[2, 0] - points[0, 0]
        ) * (points[1, 1] - points[0, 1])
        assert twice_area > 0
