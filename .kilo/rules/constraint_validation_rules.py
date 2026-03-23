"""
Constraint validation rules for GearRL system.
"""

from typing import List, Dict, Any
import numpy as np
from common.data_models import Constraints, SystemDefinition, GearLayout, Gear


class ConstraintValidationRules:
    """Rules for validating system constraints."""
    
    @staticmethod
    def validate_torque_ratio_constraint(layout: GearLayout, system: SystemDefinition) -> bool:
        """
        Validate torque ratio constraint.
        
        Args:
            layout: Current gear layout
            system: System definition with constraints
            
        Returns:
            True if constraint satisfied, False otherwise
        """
        if system.constraints.torque_ratio == "free":
            return True
            
        # Parse torque ratio
        try:
            ratio_parts = system.constraints.torque_ratio.split(":")
            if len(ratio_parts) != 2:
                return False
            target_ratio = float(ratio_parts[0]) / float(ratio_parts[1])
        except (ValueError, ZeroDivisionError):
            return False
            
        # Calculate actual ratio
        if len(layout.gears) < 2:
            return False
            
        # Find input and output gears
        input_gear = min(layout.gears, key=lambda g: 
            ((g.center.x - system.input_shaft.x)**2 + (g.center.y - system.input_shaft.y)**2)**0.5)
        output_gear = min(layout.gears, key=lambda g: 
            ((g.center.x - system.output_shaft.x)**2 + (g.center.y - system.output_shaft.y)**2)**0.5)
            
        if input_gear is output_gear:
            return False
            
        actual_ratio = input_gear.teeth_count[0] / output_gear.teeth_count[0]
        return abs(actual_ratio - target_ratio) / target_ratio <= 0.05  # 5% tolerance
    
    @staticmethod
    def validate_mass_space_ratio_constraint(layout: GearLayout, system: SystemDefinition) -> bool:
        """
        Validate mass-space ratio constraint.
        
        Args:
            layout: Current gear layout
            system: System definition with constraints
            
        Returns:
            True if constraint satisfied, False otherwise
        """
        if system.constraints.mass_space_ratio <= 0:
            return True  # No constraint
            
        # Calculate actual mass-space ratio
        total_mass = sum(sum(np.pi * (d/2)**2 for d in gear.diameters) for gear in layout.gears)
        
        # Calculate usable space (boundary area minus margin)
        boundary_points = [(p.x, p.y) for p in system.boundary.points]
        min_x, max_x = min(p[0] for p in boundary_points), max(p[0] for p in boundary_points)
        min_y, max_y = min(p[1] for p in boundary_points), max(p[1] for p in boundary_points)
        usable_area = (max_x - min_x - 2*system.constraints.boundary_margin) * \
                     (max_y - min_y - 2*system.constraints.boundary_margin)
        
        if usable_area <= 0:
            return False
            
        actual_ratio = total_mass / usable_area
        return actual_ratio <= system.constraints.mass_space_ratio
    
    @staticmethod
    def validate_boundary_margin_constraint(gear: Gear, boundary_points: List, margin: float) -> bool:
        """
        Validate boundary margin constraint for a single gear.
        
        Args:
            gear: Gear to validate
            boundary_points: Boundary polygon points
            margin: Required margin
            
        Returns:
            True if constraint satisfied, False otherwise
        """
        # Check if center is inside boundary
        if not ConstraintValidationRules._is_point_in_polygon(gear.center, boundary_points):
            return False
            
        # Check clearance
        max_radius = max(d / 2.0 for d in gear.diameters)
        required_clearance = max_radius + margin
        
        min_dist = ConstraintValidationRules._min_distance_to_boundary(gear.center, boundary_points)
        return min_dist >= required_clearance
    
    @staticmethod
    def _is_point_in_polygon(point, polygon):
        """Ray casting algorithm for point-in-polygon test."""
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0].x, polygon[0].y
        
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if min(p1y, p2y) < point.y <= max(p1y, p2y):
                if point.x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    
    @staticmethod
    def _min_distance_to_boundary(point, boundary):
        """Calculate minimum distance from point to boundary edges."""
        min_dist = float('inf')
        n = len(boundary)
        
        for i in range(n):
            p1 = boundary[i]
            p2 = boundary[(i + 1) % n]
            dist = ConstraintValidationRules._point_to_line_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist
    
    @staticmethod
    def _point_to_line_distance(point, line_p1, line_p2):
        """Calculate distance from point to line segment."""
        line_vec_x = line_p2.x - line_p1.x
        line_vec_y = line_p2.y - line_p1.y
        point_vec_x = point.x - line_p1.x
        point_vec_y = point.y - line_p1.y
        
        line_len_sq = line_vec_x**2 + line_vec_y**2
        
        if line_len_sq == 0:
            return (point_vec_x**2 + point_vec_y**2)**0.5
            
        dot = point_vec_x * line_vec_x + point_vec_y * line_vec_y
        t = max(0.0, min(1.0, dot / line_len_sq))
        
        proj_x = line_p1.x + t * line_vec_x
        proj_y = line_p1.y + t * line_vec_y
        
        return ((point.x - proj_x)**2 + (point.y - proj_y)**2)**0.5