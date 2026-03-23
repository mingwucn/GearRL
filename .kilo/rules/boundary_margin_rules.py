"""
Boundary margin rules for GearRL system.
"""

from typing import List, Dict, Any
import math
from common.data_models import Gear, Point


class BoundaryMarginRules:
    """Rules for maintaining safe margins from boundaries."""
    
    @staticmethod
    def calculate_required_margin(gear: Gear, min_margin: float) -> float:
        """
        Calculate required margin for a gear based on its size.
        
        Args:
            gear: Gear to calculate margin for
            min_margin: Minimum base margin
            
        Returns:
            Required margin distance
        """
        max_radius = max(d / 2.0 for d in gear.diameters)
        return max_radius + min_margin
    
    @staticmethod
    def validate_boundary_clearance(gear: Gear, boundary_points: List[Point], 
                                   min_margin: float) -> bool:
        """
        Validate that gear maintains proper clearance from boundary.
        
        Args:
            gear: Gear to validate
            boundary_points: Boundary polygon points
            min_margin: Minimum required margin
            
        Returns:
            True if clearance is sufficient, False otherwise
        """
        # Check if center is inside boundary
        if not BoundaryMarginRules._is_point_in_polygon(gear.center, boundary_points):
            return False
            
        required_clearance = BoundaryMarginRules.calculate_required_margin(gear, min_margin)
        actual_clearance = BoundaryMarginRules._min_distance_to_boundary(gear.center, boundary_points)
        
        return actual_clearance >= required_clearance
    
    @staticmethod
    def get_safe_placement_zone(boundary_points: List[Point], min_margin: float) -> List[tuple]:
        """
        Calculate safe placement zone by offsetting boundary inward.
        
        Args:
            boundary_points: Original boundary polygon points
            min_margin: Minimum margin to maintain
            
        Returns:
            List of points defining safe placement zone
        """
        # This is a simplified implementation - in practice, you'd use
        # polygon offset algorithms or computational geometry libraries
        safe_zone = []
        
        # For each boundary point, move it inward by margin
        for i, point in enumerate(boundary_points):
            # Get adjacent points
            prev_point = boundary_points[(i - 1) % len(boundary_points)]
            next_point = boundary_points[(i + 1) % len(boundary_points)]
            
            # Calculate inward normal vector
            # This is a simplified approach - proper implementation would use
            # angle bisectors or other computational geometry methods
            dx1 = point.x - prev_point.x
            dy1 = point.y - prev_point.y
            dx2 = next_point.x - point.x
            dy2 = next_point.y - point.y
            
            # Normalize and average direction vectors
            len1 = math.sqrt(dx1*dx1 + dy1*dy1)
            len2 = math.sqrt(dx2*dx2 + dy2*dy2)
            
            if len1 > 0 and len2 > 0:
                ux1, uy1 = dx1/len1, dy1/len1
                ux2, uy2 = dx2/len2, dy2/len2
                
                # Average direction (pointing outward)
                avg_x = (ux1 + ux2) / 2
                avg_y = (uy1 + uy2) / 2
                
                # Normalize average
                avg_len = math.sqrt(avg_x*avg_x + avg_y*avg_y)
                if avg_len > 0:
                    avg_x, avg_y = avg_x/avg_len, avg_y/avg_len
                    
                    # Move point inward (opposite direction)
                    safe_x = point.x - avg_x * min_margin
                    safe_y = point.y - avg_y * min_margin
                    safe_zone.append((safe_x, safe_y))
                else:
                    safe_zone.append((point.x, point.y))
            else:
                safe_zone.append((point.x, point.y))
                
        return safe_zone
    
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
            dist = BoundaryMarginRules._point_to_line_distance(point, p1, p2)
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