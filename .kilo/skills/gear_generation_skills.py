"""
Gear generation skills for GearRL system handling simple vs compound gears and meshing constraints.
"""

from typing import List, Dict, Any, Optional, Tuple
from common.data_models import Gear, Point, Constraints


class GearGenerator:
    """Handles gear creation with meshing constraints."""
    
    def __init__(self, module: float = 1.0):
        self.module = module
    
    def create_simple_gear(self, gear_id: str, center: Point, teeth_count: int) -> Gear:
        """
        Create a simple gear with single teeth count.
        
        Args:
            gear_id: Unique identifier for the gear
            center: Center position of the gear  
            teeth_count: Number of teeth (8-200 valid range)
            
        Returns:
            Simple gear object (teeth_count as list with single element)
        """
        if not (8 <= teeth_count <= 200):
            raise ValueError(f"Tooth count {teeth_count} outside valid range [8, 200]")
            
        return Gear(
            id=gear_id,
            center=center,
            teeth_count=[teeth_count],
            module=self.module
        )
    
    def create_compound_gear(self, gear_id: str, center: Point, teeth_counts: List[int]) -> Gear:
        """
        Create a compound gear with multiple teeth counts on the same shaft.
        
        Args:
            gear_id: Unique identifier for the gear
            center: Center position of the gear
            teeth_counts: List of teeth counts for each gear on the shaft
            
        Returns:
            Compound gear object
        """
        if not teeth_counts:
            raise ValueError("Compound gear must have at least one teeth count")
            
        for teeth_count in teeth_counts:
            if not (8 <= teeth_count <= 200):
                raise ValueError(f"Tooth count {teeth_count} outside valid range [8, 200]")
                
        return Gear(
            id=gear_id,
            center=center,
            teeth_count=teeth_counts,
            module=self.module
        )
    
    def create_gear_from_diameter(self, gear_id: str, center: Point, desired_diameter: float) -> Gear:
        """
        Create a gear by approximating desired diameter with valid tooth count.
        
        Args:
            gear_id: Unique identifier for the gear
            center: Center position of the gear
            desired_diameter: Target pitch diameter
            
        Returns:
            Gear with closest valid tooth count to achieve desired diameter
        """
        if desired_diameter <= 0:
            raise ValueError("Diameter must be positive")
            
        ideal_teeth = desired_diameter / self.module
        actual_teeth = round(ideal_teeth)
        actual_teeth = max(8, min(200, actual_teeth))
        
        return self.create_simple_gear(gear_id, center, actual_teeth)


class MeshingConstraintChecker:
    """Validates gear meshing constraints."""
    
    def __init__(self, module: float = 1.0):
        self.module = module
    
    def check_meshing_compatibility(self, gear1: Gear, gear2: Gear) -> bool:
        """
        Check if two gears can mesh properly based on their positions and sizes.
        
        Args:
            gear1: First gear
            gear2: Second gear
            
        Returns:
            True if gears can mesh, False otherwise
        """
        # Get driving diameter from first gear (last element)
        driving_radius = (gear1.diameters[-1]) / 2.0
        # Get driven diameter from second gear (first element)
        driven_radius = (gear2.diameters[0]) / 2.0
        
        # Calculate actual distance between centers
        dx = gear1.center.x - gear2.center.x
        dy = gear1.center.y - gear2.center.y
        actual_distance = (dx**2 + dy**2)**0.5
        
        # Required distance for proper meshing
        required_distance = driving_radius + driven_radius
        
        # Allow small tolerance for floating point precision
        return abs(actual_distance - required_distance) < 1e-3
    
    def get_required_center_distance(self, teeth1: int, teeth2: int) -> float:
        """
        Calculate required center-to-center distance for two gears to mesh.
        
        Args:
            teeth1: Teeth count of first gear
            teeth2: Teeth count of second gear
            
        Returns:
            Required center distance for proper meshing
        """
        radius1 = (self.module * teeth1) / 2.0
        radius2 = (self.module * teeth2) / 2.0
        return radius1 + radius2
    
    def validate_gear_placement(self, new_gear: Gear, existing_gears: List[Gear], 
                               boundary_points: List[Point], constraints: Constraints) -> bool:
        """
        Validate that a new gear placement doesn't violate constraints.
        
        Args:
            new_gear: Gear to validate
            existing_gears: List of already placed gears
            boundary_points: Boundary polygon points
            constraints: Design constraints
            
        Returns:
            True if placement is valid, False otherwise
        """
        # Check collision with existing gears
        for existing_gear in existing_gears:
            if self._check_gear_collision(new_gear, existing_gear):
                return False
                
        # Check boundary containment with margin
        if not self._check_boundary_containment(new_gear, boundary_points, constraints.boundary_margin):
            return False
            
        # Check size constraints
        max_teeth = max(new_gear.teeth_count)
        min_teeth = min(new_gear.teeth_count)
        if min_teeth < constraints.min_gear_size or max_teeth > constraints.max_gear_size:
            return False
            
        return True
    
    def _check_gear_collision(self, gear1: Gear, gear2: Gear) -> bool:
        """Check if two gears collide."""
        # Get maximum radii for collision detection
        max_radius1 = max(d / 2.0 for d in gear1.diameters)
        max_radius2 = max(d / 2.0 for d in gear2.diameters)
        
        dx = gear1.center.x - gear2.center.x
        dy = gear1.center.y - gear2.center.y
        distance = (dx**2 + dy**2)**0.5
        min_required_distance = max_radius1 + max_radius2
        
        return distance < min_required_distance - 1e-5
    
    def _check_boundary_containment(self, gear: Gear, boundary_points: List[Point], 
                                   margin: float) -> bool:
        """Check if gear fits within boundary with specified margin."""
        # Check if center is inside boundary
        if not self._is_point_in_polygon(gear.center, boundary_points):
            return False
            
        # Get maximum radius of gear
        max_radius = max(d / 2.0 for d in gear.diameters)
        required_clearance = max_radius + margin
        
        # Check minimum distance to boundary
        min_dist = self._min_distance_to_boundary(gear.center, boundary_points)
        return min_dist >= required_clearance
    
    def _is_point_in_polygon(self, point: Point, polygon: List[Point]) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0].x, polygon[0].y
        
        for i in range(1, n + 1):
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
    
    def _min_distance_to_boundary(self, point: Point, boundary: List[Point]) -> float:
        """Calculate minimum distance from point to boundary edges."""
        min_dist = float('inf')
        n = len(boundary)
        
        for i in range(n):
            p1 = boundary[i]
            p2 = boundary[(i + 1) % n]
            dist = self._point_to_line_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist
    
    def _point_to_line_distance(self, point: Point, line_p1: Point, line_p2: Point) -> float:
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