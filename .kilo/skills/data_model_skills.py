"""
Data model skills for GearRL system handling SystemDefinition, GearLayout, and ValidationReport.
Provides serialization, validation, and transformation utilities.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
import json
import numpy as np
from common.data_models import SystemDefinition, GearLayout, ValidationReport, Constraints, Point, Boundary, Gear


class DataModelSkill:
    """Base class for data model operations."""
    
    @staticmethod
    def serialize_system_definition(system: SystemDefinition) -> Dict[str, Any]:
        """Serialize SystemDefinition to JSON-compatible dictionary."""
        return system.to_json()
    
    @staticmethod
    def deserialize_system_definition(data: Dict[str, Any]) -> SystemDefinition:
        """Deserialize SystemDefinition from JSON-compatible dictionary."""
        return SystemDefinition.from_json(data)
    
    @staticmethod
    def serialize_gear_layout(layout: GearLayout) -> List[Dict[str, Any]]:
        """Serialize GearLayout to JSON-compatible list."""
        return layout.to_json()
    
    @staticmethod
    def deserialize_gear_layout(data: List[Dict[str, Any]]) -> GearLayout:
        """Deserialize GearLayout from JSON-compatible list."""
        return GearLayout.from_json(data)
    
    @staticmethod
    def serialize_validation_report(report: ValidationReport) -> Dict[str, Any]:
        """Serialize ValidationReport to JSON-compatible dictionary."""
        return report.to_json()


class CoordinateTransformer:
    """Handles coordinate transformations between different spaces."""
    
    @staticmethod
    def pixel_to_normalized(pixel_coords: List[Tuple[float, float]], 
                          normalization_params: Dict[str, float]) -> List[Tuple[float, float]]:
        """Transform pixel coordinates to normalized space."""
        scale = normalization_params['scale']
        offset_x = normalization_params['offset_x']
        offset_y = normalization_params['offset_y']
        
        normalized = []
        for x, y in pixel_coords:
            norm_x = x * scale + offset_x
            norm_y = y * scale + offset_y
            normalized.append((norm_x, norm_y))
        return normalized
    
    @staticmethod
    def normalized_to_pixel(normalized_coords: List[Tuple[float, float]], 
                          normalization_params: Dict[str, float]) -> List[Tuple[float, float]]:
        """Transform normalized coordinates back to pixel space."""
        scale = normalization_params['scale']
        offset_x = normalization_params['offset_x']
        offset_y = normalization_params['offset_y']
        
        pixel = []
        for x, y in normalized_coords:
            pixel_x = (x - offset_x) / scale
            pixel_y = (y - offset_y) / scale
            pixel.append((pixel_x, pixel_y))
        return pixel


class SystemValidator:
    """Validates system definitions and constraints."""
    
    @staticmethod
    def validate_constraints(constraints: Constraints) -> bool:
        """Validate constraint values are within reasonable bounds."""
        if not (0.1 <= constraints.mass_space_ratio <= 10.0):
            return False
        if not (0.1 <= constraints.boundary_margin <= 50.0):
            return False
        if not (8 <= constraints.min_gear_size <= 50):
            return False
        if not (20 <= constraints.max_gear_size <= 200):
            return False
        return True
    
    @staticmethod
    def validate_boundary(boundary: Boundary) -> bool:
        """Validate boundary has sufficient points and forms a valid polygon."""
        if len(boundary.points) < 3:
            return False
        # Check for duplicate consecutive points
        for i in range(len(boundary.points)):
            p1 = boundary.points[i]
            p2 = boundary.points[(i + 1) % len(boundary.points)]
            if abs(p1.x - p2.x) < 1e-6 and abs(p1.y - p2.y) < 1e-6:
                return False
        return True