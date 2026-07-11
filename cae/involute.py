"""Involute spur-gear geometry primitives used by the CAE meshing workflow."""

from __future__ import annotations

from math import acos, cos, pi, sin, sqrt

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
