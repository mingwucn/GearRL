"""
Utility functions for GearRL system.
Provides common helper functions that don't fit into specific skill categories.
"""

import math
from typing import List, Tuple, Optional
from common.data_models import Point


class GeometryUtils:
    """Common geometry utility functions."""
    
    @staticmethod
    def distance(p1: Point, p2: Point) -> float:
        """
        Calculate Euclidean distance between two points.
        
        Args:
            p1: First point
            p2: Second point
            
        Returns:
            Distance between points
        """
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
    @staticmethod
    def point_to_line_distance(point: Point, line_p1: Point, line_p2: Point) -> float:
        """
        Calculate shortest distance from point to line segment.
        
        Args:
            point: Point to measure from
            line_p1: First endpoint of line segment
            line_p2: Second endpoint of line segment
            
        Returns:
            Shortest distance from point to line segment
        """
        # Vector from line_p1 to line_p2
        line_vec = Point(line_p2.x - line_p1.x, line_p2.y - line_p1.y)
        # Vector from line_p1 to point
        point_vec = Point(point.x - line_p1.x, point.y - line_p1.y)
        
        # Length of line segment squared
        line_len_sq = line_vec.x**2 + line_vec.y**2
        
        # Dot product
        dot = point_vec.x * line_vec.x + point_vec.y * line_vec.y
        
        # Calculate projection
        if line_len_sq == 0:
            return GeometryUtils.distance(point, line_p1)
            
        t = max(0, min(1, dot / line_len_sq))
        
        # Projection point
        proj = Point(
            line_p1.x + t * line_vec.x,
            line_p1.y + t * line_vec.y
        )
        
        return GeometryUtils.distance(point, proj)
    
    @staticmethod
    def is_point_in_polygon(point: Point, polygon: List[Point]) -> bool:
        """
        Ray casting algorithm for point-in-polygon test.
        
        Args:
            point: Point to test
            polygon: List of points defining polygon vertices
            
        Returns:
            True if point is inside polygon, False otherwise
        """
        n = len(polygon)
        if n < 3:
            return False
            
        inside = False
        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if point.y > min(p1y, p2y):
                if point.y <= max(p1y, p2y):
                    if point.x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    
    @staticmethod
    def min_distance_to_boundary(point: Point, boundary: List[Point]) -> float:
        """
        Calculate minimum distance from point to boundary edges.
        
        Args:
            point: Point to measure from
            boundary: List of points defining boundary polygon
            
        Returns:
            Minimum distance from point to boundary
        """
        min_dist = float('inf')
        n = len(boundary)
        
        # Check distance to all vertices
        for vertex in boundary:
            dist = GeometryUtils.distance(point, vertex)
            if dist < min_dist:
                min_dist = dist
        
        # Check distance to edges
        for i in range(n):
            p1 = boundary[i]
            p2 = boundary[(i + 1) % n]
            dist = GeometryUtils.point_to_line_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist


class MathUtils:
    """Common mathematical utility functions."""
    
    @staticmethod
    def is_close(a: float, b: float, rel_tol: float = 1e-9, abs_tol: float = 0.0) -> bool:
        """
        Check if two floating point numbers are close.
        
        Args:
            a: First number
            b: Second number  
            rel_tol: Relative tolerance
            abs_tol: Absolute tolerance
            
        Returns:
            True if numbers are close within specified tolerances
        """
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
    
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """
        Clamp value between minimum and maximum bounds.
        
        Args:
            value: Value to clamp
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Clamped value
        """
        return max(min_val, min(value, max_val))


class FileUtils:
    """Common file utility functions."""
    
    @staticmethod
    def ensure_directory_exists(filepath: str) -> None:
        """
        Ensure directory exists for given file path.
        
        Args:
            filepath: Path to file
        """
        import os
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


# Convenience function aliases
distance = GeometryUtils.distance
point_to_line_distance = GeometryUtils.point_to_line_distance  
is_point_in_polygon = GeometryUtils.is_point_in_polygon
min_distance_to_boundary = GeometryUtils.min_distance_to_boundary
is_close = MathUtils.is_close
clamp = MathUtils.clamp
ensure_directory_exists = FileUtils.ensure_directory_exists
