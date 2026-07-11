"""Minimal dependency-free SVG and DXF exports for certified GearTrain layouts."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from common.design_models import GearTrain


def export_svg(train: GearTrain, output_path: str | Path, padding_mm: float = 5.0) -> Path:
    """Export pitch and outer circles to a scalable, auditable SVG."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    min_x, min_y, width, height = _bounds(train, padding_mm)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x} {min_y} {width} {height}">',
        '<g fill="none" stroke="#1f2937" stroke-width="0.25">',
    ]
    for stage in train.stages:
        for member, teeth in enumerate(stage.teeth):
            pitch = stage.pitch_radius_mm(member)
            outer = stage.module_mm * (teeth + 2) / 2.0
            elements.append(f'<circle cx="{stage.center.x}" cy="{stage.center.y}" r="{outer}" stroke="#0f766e"/>')
            elements.append(f'<circle cx="{stage.center.x}" cy="{stage.center.y}" r="{pitch}" stroke="#64748b" stroke-dasharray="0.8 0.8"/>')
        elements.append(f'<circle cx="{stage.center.x}" cy="{stage.center.y}" r="0.5" fill="#111827"/>')
    elements.extend(["</g>", f"<metadata>{escape(','.join(stage.id for stage in train.stages))}</metadata>", "</svg>"])
    destination.write_text("\n".join(elements) + "\n")
    return destination


def export_dxf(train: GearTrain, output_path: str | Path) -> Path:
    """Export pitch and outer circles as an ASCII DXF R12 drawing."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = ["0", "SECTION", "2", "ENTITIES"]
    for stage in train.stages:
        for member, teeth in enumerate(stage.teeth):
            for layer, radius in (("OUTER", stage.module_mm * (teeth + 2) / 2.0), ("PITCH", stage.pitch_radius_mm(member))):
                records.extend(["0", "CIRCLE", "8", layer, "10", str(stage.center.x), "20", str(stage.center.y), "30", str(stage.layer(member)), "40", str(radius)])
    records.extend(["0", "ENDSEC", "0", "EOF"])
    destination.write_text("\n".join(records) + "\n")
    return destination


def _bounds(train: GearTrain, padding_mm: float) -> tuple[float, float, float, float]:
    if padding_mm < 0 or not train.stages:
        raise ValueError("A non-empty train and non-negative padding are required")
    min_x = min(stage.center.x - stage.outer_radius_mm() for stage in train.stages) - padding_mm
    min_y = min(stage.center.y - stage.outer_radius_mm() for stage in train.stages) - padding_mm
    max_x = max(stage.center.x + stage.outer_radius_mm() for stage in train.stages) + padding_mm
    max_y = max(stage.center.y + stage.outer_radius_mm() for stage in train.stages) + padding_mm
    return min_x, min_y, max_x - min_x, max_y - min_y
