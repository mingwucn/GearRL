"""Involute spur-gear geometry primitives used by the CAE meshing workflow."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, cos, pi, sin, sqrt, tan

import numpy as np


class InvoluteGeometry:
    """Parametric involute geometry owned by the CAE subsystem."""

    @staticmethod
    def point(base_radius_mm: float, roll_angle_rad: float) -> tuple[float, float]:
        if base_radius_mm <= 0 or roll_angle_rad < 0:
            raise ValueError("Base radius must be positive and roll angle non-negative")
        return (
            base_radius_mm * (cos(roll_angle_rad) + roll_angle_rad * sin(roll_angle_rad)),
            base_radius_mm * (sin(roll_angle_rad) - roll_angle_rad * cos(roll_angle_rad)),
        )

    @classmethod
    def flank(cls, module_mm: float, teeth: int, pressure_angle_deg: float = 20.0, samples: int = 24) -> np.ndarray:
        """Return one involute flank from pitch circle to the standard addendum."""
        if module_mm <= 0 or teeth < 3 or samples < 2:
            raise ValueError("Invalid involute geometry parameters")
        pressure_angle = pressure_angle_deg * pi / 180.0
        pitch_radius = cls.pitch_radius(module_mm, teeth)
        base_radius = pitch_radius * cos(pressure_angle)
        outer_radius = pitch_radius + module_mm
        max_roll = sqrt((outer_radius / base_radius) ** 2 - 1.0)
        rolls = np.linspace(0.0, max_roll, samples)
        return np.asarray([cls.point(base_radius, roll) for roll in rolls])

    @staticmethod
    def pitch_radius(module_mm: float, teeth: int) -> float:
        if module_mm <= 0 or teeth <= 0:
            raise ValueError("Module and tooth count must be positive")
        return module_mm * teeth / 2.0


@dataclass(frozen=True)
class ToothSectionGeometry:
    """Symmetric local tooth section with radial y and tangential half-width."""

    radial_positions_mm: np.ndarray
    half_widths_mm: np.ndarray
    root_radius_mm: float
    base_radius_mm: float
    pitch_radius_mm: float
    outer_radius_mm: float
    fillet_radius_mm: float
    pitch_half_width_mm: float

    def __post_init__(self) -> None:
        radial = np.asarray(self.radial_positions_mm, dtype=float)
        widths = np.asarray(self.half_widths_mm, dtype=float)
        if radial.ndim != 1 or widths.shape != radial.shape or len(radial) < 4:
            raise ValueError("A tooth section requires matching one-dimensional profile arrays")
        if radial[0] != 0.0 or np.any(np.diff(radial) <= 0) or np.any(widths <= 0):
            raise ValueError("Tooth section profile must be positive and radially ordered")
        object.__setattr__(self, "radial_positions_mm", radial)
        object.__setattr__(self, "half_widths_mm", widths)

    @property
    def height_mm(self) -> float:
        return float(self.radial_positions_mm[-1])

    @property
    def root_width_mm(self) -> float:
        return float(2.0 * self.half_widths_mm[0])

    def half_width(self, radial_position_mm: float) -> float:
        if radial_position_mm < 0 or radial_position_mm > self.height_mm:
            raise ValueError("Radial position lies outside the tooth section")
        return float(np.interp(radial_position_mm, self.radial_positions_mm, self.half_widths_mm))


class InvoluteToothSectionFactory:
    """Create a standard full-depth involute tooth with an explicit root fillet."""

    def __init__(self, flank_samples: int = 32, fillet_samples: int = 10):
        if flank_samples < 4 or fillet_samples < 3:
            raise ValueError("Tooth-section sampling must resolve flank and fillet")
        self._flank_samples = flank_samples
        self._fillet_samples = fillet_samples

    def create(self, module_mm: float, teeth: int, pressure_angle_deg: float = 20.0) -> ToothSectionGeometry:
        if module_mm <= 0 or teeth < 3 or not 0 < pressure_angle_deg < 90:
            raise ValueError("Invalid involute tooth-section parameters")
        pressure_angle = pressure_angle_deg * pi / 180.0
        pitch_radius = module_mm * teeth / 2.0
        base_radius = pitch_radius * cos(pressure_angle)
        root_radius = pitch_radius - 1.25 * module_mm
        outer_radius = pitch_radius + module_mm
        if root_radius <= 0:
            raise ValueError("Standard tooth section requires a positive root circle")

        pitch_roll = tan(pressure_angle)
        pitch_involute_angle = pitch_roll - atan(pitch_roll)
        pitch_half_angle = pi / (2.0 * teeth)
        rotation = pitch_half_angle - pitch_involute_angle
        minimum_roll = sqrt(max(0.0, (root_radius / base_radius) ** 2 - 1.0))
        maximum_roll = sqrt((outer_radius / base_radius) ** 2 - 1.0)
        rolls = np.linspace(minimum_roll, maximum_roll, self._flank_samples)
        flank_x = []
        flank_y = []
        for roll in rolls:
            raw_x, raw_y = InvoluteGeometry.point(base_radius, float(roll))
            rotated_x = raw_x * cos(rotation) - raw_y * sin(rotation)
            rotated_y = raw_x * sin(rotation) + raw_y * cos(rotation)
            # Convert from gear-centred Cartesian coordinates to local tooth
            # coordinates: tangential x and radial height above the root circle.
            flank_x.append(rotated_y)
            flank_y.append(rotated_x)

        base_half_width = flank_x[0]
        natural_gap = flank_y[0] - root_radius
        fillet_radius = natural_gap if natural_gap > 0.05 * module_mm else 0.30 * module_mm
        root_datum = flank_y[0] - fillet_radius
        flank_y = [value - root_datum for value in flank_y]
        angles = np.linspace(0.0, pi / 2.0, self._fillet_samples)
        fillet_x = base_half_width + fillet_radius * np.cos(angles)
        fillet_y = fillet_radius - fillet_radius * np.cos(angles)
        radial = np.concatenate((fillet_y[:-1], np.asarray(flank_y)))
        widths = np.concatenate((fillet_x[:-1], np.asarray(flank_x)))
        order = np.argsort(radial, kind="stable")
        radial = radial[order]
        widths = widths[order]
        keep = np.concatenate(([True], np.diff(radial) > 1e-12))
        return ToothSectionGeometry(
            radial[keep],
            widths[keep],
            root_radius,
            base_radius,
            pitch_radius,
            outer_radius,
            fillet_radius,
            pitch_radius * sin(pitch_half_angle),
        )
