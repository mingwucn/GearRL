"""
Gear placement rules for GearRL system.
"""

from typing import List, Dict, Any
import math
from common.data_models import Gear, Point, Constraints


class GearPlacementRules:
    """Rules governing valid gear placement."""
    
    @staticmethod
    def validate_minimum_gear_size(gear: Gear, min_size: int) -> bool:
        """
        Validate that gear meets minimum size requirement.
        
        Args:
            gear: Gear to validate
            min_size: Minimum teeth count allowed
            
        Returns:
            True if valid, False otherwise
        """
        return min(gear.teeth_count) >= min_size
    
    @staticmethod
    def validate_maximum_gear_size(gear: Gear, max_size: int) -> bool:
        """
        Validate that gear meets maximum size requirement.
        
        Args:
            gear: Gear to validate
            max_size: Maximum teeth count allowed
            
        Returns:
            True if valid, False otherwise
        """
        return max(gear.teeth_count) <= max_size
    
    @staticmethod
    def validate_gear_spacing(gear1: Gear, gear2: Gear, min_clearance: float = 0.0) -> bool:
        """
        Validate minimum spacing between gears (for non-meshing gears).
        
        Args:
            gear1: First gear
            gear2: Second gear
            min_clearance: Minimum clearance required between non-meshing gears
            
        Returns:
            True if spacing is valid, False otherwise
        """
        # Get maximum radii for collision detection
        max_radius1 = max(d / 2.0 for d in gear1.diameters)
        max_radius2 = max(d / 2.0 for d in gear2.diameters)
        
        # Calculate distance between centers
        dx = gear1.center.x - gear2.center.x
        dy = gear1.center.y - gear2.center.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Required minimum distance
        min_required = max_radius1 + max_radius2 + min_clearance
        
        return distance >= min_required
    
    @staticmethod
    def validate_center_position(center: Point, boundary_points: List[Point], 
                                margin: float = 0.0) -> bool:
        """
        Validate that a gear center position is within boundary with margin.
        
        Args:
            center: Proposed gear center
            boundary_points: Boundary polygon points
            margin: Additional margin beyond gear radius
            
        Returns:
            True if position is valid, False otherwise
        """
        # Check if center is inside boundary
        if not GearPlacementRules._is_point_in_polygon(center, boundary_points):
            return False
            
        # Check distance to boundary (margin will be added when checking against actual gear radius)
        min_dist = GearPlacementRules._min_distance_to_boundary(center, boundary_points)
        return min_dist >= margin
    
    @staticmethod
    def _is_point_in_polygon(point: Point, polygon: List[Point]) -> bool:
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
    def _min_distance_to_boundary(point: Point, boundary: List[Point]) -> float:
        """Calculate minimum distance from point to boundary edges."""
        min_dist = float('inf')
        n = len(boundary)
        
        for i in range(n):
            p1 = boundary[i]
            p2 = boundary[(i + 1) % n]
            dist = GearPlacementRules._point_to_line_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist
    
    @staticmethod
    def _point_to_line_distance(point: Point, line_p1: Point, line_p2: Point) -> float:
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