"""Gmsh command-line adapter for reproducible planar finite-element meshes."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

import meshio
import numpy as np

from cae.linear_elastic import TriangularMesh


class GmshMesher:
    """Adapter that owns Gmsh invocation and GearRL mesh normalization."""

    def mesh(self, points_mm: Sequence[tuple[float, float]], thickness_mm: float, max_element_size_mm: float) -> TriangularMesh:
        """Mesh a simple planar polygon using the external Gmsh executable.

    Gmsh performs only triangulation.  Element orientation normalization and all
    material/solver work stay inside the GearRL CAE implementation.
    """
        if len(points_mm) < 3 or thickness_mm <= 0 or max_element_size_mm <= 0:
            raise ValueError("A polygon, positive thickness, and mesh size are required")
        if shutil.which("gmsh") is None:
            raise RuntimeError("gmsh executable is required; update conda env ai")
        with tempfile.TemporaryDirectory(prefix="gearrl-gmsh-") as directory:
            root = Path(directory)
            geometry_path = root / "polygon.geo"
            mesh_path = root / "polygon.msh"
            geometry_path.write_text(self._geo_script(points_mm, max_element_size_mm))
            completed = subprocess.run(
                ["gmsh", "-2", "-format", "msh2", "-o", str(mesh_path), str(geometry_path)],
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"Gmsh failed: {completed.stderr.strip()}")
            mesh = meshio.read(mesh_path)
        triangles = mesh.cells_dict.get("triangle")
        if triangles is None or not len(triangles):
            raise RuntimeError("Gmsh did not produce triangular elements")
        nodes = np.asarray(mesh.points[:, :2], dtype=float)
        elements = np.asarray(triangles, dtype=int)
        for index, element in enumerate(elements):
            coords = nodes[element]
            twice_area = (coords[1, 0] - coords[0, 0]) * (coords[2, 1] - coords[0, 1]) - (
                coords[2, 0] - coords[0, 0]
            ) * (coords[1, 1] - coords[0, 1])
            if twice_area < 0:
                elements[index, [1, 2]] = elements[index, [2, 1]]
        return TriangularMesh(nodes, elements, thickness_mm)

    @staticmethod
    def _geo_script(points_mm: Sequence[tuple[float, float]], max_element_size_mm: float) -> str:
        point_lines = [f"Point({index + 1}) = {{{x}, {y}, 0, {max_element_size_mm}}};" for index, (x, y) in enumerate(points_mm)]
        line_lines = []
        for index in range(len(points_mm)):
            start = index + 1
            end = (index + 1) % len(points_mm) + 1
            line_lines.append(f"Line({index + 1}) = {{{start}, {end}}};")
        ids = ", ".join(str(index + 1) for index in range(len(points_mm)))
        return "\n".join([
            "Mesh.Algorithm = 6;",
            *point_lines,
            *line_lines,
            f"Curve Loop(1) = {{{ids}}};",
            "Plane Surface(1) = {1};",
            "Mesh 2;",
        ])
