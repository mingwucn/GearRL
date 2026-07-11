"""Certificate-first manufacturing export workflow for certified GearRL layouts."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from common.design_models import DesignProblem, GearTrain, ManufacturingArtifact
from manufacturing.exporters import ManufacturingExporter
from physics_validator.reference_verifier import ReferenceVerifier


class ManufacturingWorkflow:
    """Create auditable DXF/SVG concept artifacts only for valid certified trains."""

    def __init__(self, exporter: ManufacturingExporter | None = None):
        self._exporter = exporter or ManufacturingExporter()

    def export(self, problem: DesignProblem, train: GearTrain, output_directory: str | Path) -> ManufacturingArtifact:
        certificate = ReferenceVerifier.verify_with_cae(problem, train)
        if not certificate.valid:
            raise ValueError("Manufacturing export requires an independently valid certificate")
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)
        artifact_id = str(uuid4())
        svg = self._exporter.export_svg(train, directory / f"{artifact_id}.svg")
        dxf = self._exporter.export_dxf(train, directory / f"{artifact_id}.dxf")
        artifact = ManufacturingArtifact(artifact_id, str(svg), str(dxf), certificate.to_json())
        (directory / f"{artifact_id}.json").write_text(json.dumps(artifact.to_json(), indent=2, sort_keys=True) + "\n")
        return artifact
