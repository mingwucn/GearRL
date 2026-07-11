"""Deterministic SVG publication figures from frozen GearRL evidence."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from math import log10
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from reporting.artifact_registry import EvidenceSource


class SVGCanvas:
    """Small structured vector renderer for evidence plots."""

    WIDTH = 1200
    HEIGHT = 700
    LEFT = 135
    RIGHT = 1140
    TOP = 75
    BOTTOM = 580

    def __init__(self, title: str, x_label: str, y_label: str):
        self.root = Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": str(self.WIDTH),
                "height": str(self.HEIGHT),
                "viewBox": f"0 0 {self.WIDTH} {self.HEIGHT}",
                "role": "img",
                "aria-label": title,
            },
        )
        SubElement(self.root, "rect", {"width": "1200", "height": "700", "fill": "#FFFFFF"})
        self.text(600, 36, title, 24, "middle", "#17212B", "600")
        self.text(635, 670, x_label, 18, "middle", "#263746")
        self.text(28, 330, y_label, 18, "middle", "#263746", transform="rotate(-90 28 330)")

    def axes(self, maximum: float, ticks: int = 5, formatter=None) -> None:
        formatter = formatter or (lambda value: f"{value:g}")
        for index in range(ticks + 1):
            value = maximum * index / ticks
            y = self.BOTTOM - (self.BOTTOM - self.TOP) * index / ticks
            self.line(self.LEFT, y, self.RIGHT, y, "#D9DEE3", 1)
            self.text(self.LEFT - 14, y + 6, formatter(value), 14, "end", "#425466")
        self.line(self.LEFT, self.TOP, self.LEFT, self.BOTTOM, "#334E5C", 2)
        self.line(self.LEFT, self.BOTTOM, self.RIGHT, self.BOTTOM, "#334E5C", 2)

    def bar(self, center: float, value: float, maximum: float, width: float, color: str, label: str) -> None:
        height = (self.BOTTOM - self.TOP) * value / maximum
        y = self.BOTTOM - height
        SubElement(
            self.root,
            "rect",
            {"x": f"{center - width / 2:.3f}", "y": f"{y:.3f}", "width": f"{width:.3f}", "height": f"{height:.3f}", "fill": color},
        )
        self.text(center, self.BOTTOM + 30, label, 15, "middle", "#263746")

    def error_bar(self, x: float, lower: float, upper: float, maximum: float) -> None:
        y_low = self.BOTTOM - (self.BOTTOM - self.TOP) * lower / maximum
        y_high = self.BOTTOM - (self.BOTTOM - self.TOP) * upper / maximum
        self.line(x, y_low, x, y_high, "#17212B", 3)
        self.line(x - 12, y_low, x + 12, y_low, "#17212B", 3)
        self.line(x - 12, y_high, x + 12, y_high, "#17212B", 3)

    def circle(self, x: float, y: float, radius: float, color: str) -> None:
        SubElement(self.root, "circle", {"cx": f"{x:.3f}", "cy": f"{y:.3f}", "r": f"{radius:.3f}", "fill": color, "stroke": "#FFFFFF", "stroke-width": "3"})

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float) -> None:
        SubElement(self.root, "line", {"x1": f"{x1:.3f}", "y1": f"{y1:.3f}", "x2": f"{x2:.3f}", "y2": f"{y2:.3f}", "stroke": color, "stroke-width": f"{width:.3f}"})

    def text(
        self, x: float, y: float, value: str, size: int, anchor: str, color: str, weight: str = "400", transform: str | None = None
    ) -> None:
        attributes = {
            "x": f"{x:.3f}", "y": f"{y:.3f}", "font-family": "Arial, sans-serif", "font-size": str(size),
            "text-anchor": anchor, "fill": color, "font-weight": weight, "letter-spacing": "0",
        }
        if transform:
            attributes["transform"] = transform
        SubElement(self.root, "text", attributes).text = value

    def bytes(self) -> bytes:
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(self.root, encoding="utf-8") + b"\n"


class PublicationFigure(ABC):
    """Strategy contract for one evidence-only vector publication figure."""

    COLORS = ("#2374AB", "#F18F01", "#2A9D55", "#C44536")

    @property
    @abstractmethod
    def figure_id(self) -> str:
        """Stable figure identifier."""

    @property
    @abstractmethod
    def sources(self) -> tuple[EvidenceSource, ...]:
        """Every frozen payload read by the renderer."""

    @abstractmethod
    def render(self) -> bytes:
        """Return a deterministic SVG document."""

    @staticmethod
    def _json(path: Path) -> dict:
        return json.loads(path.read_text())


class SolverComparisonFigure(PublicationFigure):
    def __init__(self, source: Path):
        self._source = source

    @property
    def figure_id(self) -> str:
        return "solver-runtime-candidates"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (EvidenceSource("requirements-comparison-adjudication-v2", self._source),)

    def render(self) -> bytes:
        methods = self._json(self._source)["methods"]
        canvas = SVGCanvas("Bounded solver comparison", "Median candidate evaluations (log10)", "Median runtime (log10 s)")
        x_values = [log10(value["median_parameter_tuples_across_runs"]) for value in methods.values()]
        y_values = [log10(value["median_runtime_s_across_runs"]) for value in methods.values()]
        x_min, x_max = min(x_values) - 0.3, max(x_values) + 0.3
        y_min, y_max = min(y_values) - 0.3, max(y_values) + 0.3
        canvas.axes(y_max - y_min, formatter=lambda value: f"{value + y_min:.1f}")
        for index, (method, values) in enumerate(sorted(methods.items())):
            x_value = log10(values["median_parameter_tuples_across_runs"])
            y_value = log10(values["median_runtime_s_across_runs"])
            x = canvas.LEFT + (canvas.RIGHT - canvas.LEFT) * (x_value - x_min) / (x_max - x_min)
            y = canvas.BOTTOM - (canvas.BOTTOM - canvas.TOP) * (y_value - y_min) / (y_max - y_min)
            canvas.circle(x, y, 14, self.COLORS[index])
            canvas.text(x + 18, y - 12, method, 15, "start", "#263746", "600")
            canvas.text(x, canvas.BOTTOM + 28, f"{x_value:.1f}", 13, "middle", "#425466")
        return canvas.bytes()


class FailureProbabilityFigure(PublicationFigure):
    def __init__(self, manifest: Path, results: Path):
        self._manifest, self._results = manifest, results

    @property
    def figure_id(self) -> str:
        return "material-failure-probability"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (EvidenceSource("load-uncertainty-v1-manifest", self._manifest), EvidenceSource("load-uncertainty-v1-results", self._results))

    def render(self) -> bytes:
        materials = self._json(self._results)["materials"]
        maximum = 0.25
        canvas = SVGCanvas("Conditional static-screen failure probability", "Material condition", "Failure probability")
        canvas.axes(maximum, formatter=lambda value: f"{value:.2f}")
        centers = (400, 850)
        for index, (center, material) in enumerate(zip(centers, materials)):
            value = material["pooled_failure_probability"]
            canvas.bar(center, value, maximum, 210, self.COLORS[index], material["material_name"])
            canvas.error_bar(center, *material["layout_bootstrap_ci95"], maximum)
            canvas.text(center, canvas.BOTTOM - (canvas.BOTTOM - canvas.TOP) * value / maximum - 20, f"{value:.3f}", 17, "middle", "#17212B", "600")
        return canvas.bytes()


class SensitivityIndicesFigure(PublicationFigure):
    def __init__(self, manifest: Path, results: Path):
        self._manifest, self._results = manifest, results

    @property
    def figure_id(self) -> str:
        return "load-total-order-sensitivity"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (EvidenceSource("load-uncertainty-v1-manifest", self._manifest), EvidenceSource("load-uncertainty-v1-results", self._results))

    def render(self) -> bytes:
        indices = self._json(self._results)["materials"][0]["sensitivity"]
        canvas = SVGCanvas("Operating-parameter sensitivity", "Uncertain parameter", "Mean total-order Sobol index")
        canvas.axes(1.0, formatter=lambda value: f"{value:.1f}")
        centers = (310, 635, 960)
        for index, (center, item) in enumerate(zip(centers, indices)):
            value = item["total_order"]
            label = item["parameter"].replace("_", " ").title()
            canvas.bar(center, value, 1.0, 180, self.COLORS[index], label)
            canvas.text(center, max(canvas.TOP + 24, canvas.BOTTOM - (canvas.BOTTOM - canvas.TOP) * value - 18), f"{value:.3f}", 17, "middle", "#17212B", "600")
        return canvas.bytes()


class StrengthCouplingFigure(PublicationFigure):
    def __init__(self, manifest: Path, summary: Path):
        self._manifest, self._summary = manifest, summary

    @property
    def figure_id(self) -> str:
        return "strength-coupling-outcomes"

    @property
    def sources(self) -> tuple[EvidenceSource, ...]:
        return (EvidenceSource("strength-coupled-v1-manifest", self._manifest), EvidenceSource("strength-coupled-v1-summary", self._summary))

    def render(self) -> bytes:
        summary = self._json(self._summary)
        labels = ("Retained", "Redesigned", "Rejected")
        values = (summary["retained_count"], summary["redesigned_count"], summary["rejected_count"])
        colors = (self.COLORS[2], self.COLORS[1], self.COLORS[3])
        canvas = SVGCanvas("Effect of static-strength admission", "Synthesis outcome", "Predeclared cases")
        canvas.axes(8.0, formatter=lambda value: f"{value:.0f}")
        for center, label, value, color in zip((310, 635, 960), labels, values, colors):
            canvas.bar(center, value, 8.0, 180, color, label)
            canvas.text(center, canvas.BOTTOM - (canvas.BOTTOM - canvas.TOP) * value / 8.0 - 18, str(value), 18, "middle", "#17212B", "600")
        return canvas.bytes()
