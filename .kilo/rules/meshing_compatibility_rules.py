"""
Meshing compatibility rules for GearRL system.
"""

from typing import List, Dict, Any
import math
from common.data_models import Gear


class MeshingCompatibilityRules:
    """Rules for gear meshing compatibility."""
    
    def __init__(self, module: float = 1.0):
        self.module = module
    
    def validate_meshing_pair(self, driving_gear: Gear, driven_gear: Gear, 
                             tolerance: float = 1e-3) -> bool:
        """
        Validate that two gears can mesh properly.
        
        Args:
            driving_gear: Gear that drives (output gear)
            driven_gear: Gear that is driven (input gear)
            tolerance: Tolerance for distance matching
            
        Returns:
            True if gears can mesh, False otherwise
        """
        # Get driving diameter from driving gear (last element in compound gear)
        driving_radius = driving_gear.diameters[-1] / 2.0
        # Get driven diameter from driven gear (first element in compound gear)
        driven_radius = driven_gear.diameters[0] / 2.0
        
        # Calculate actual distance between centers
        dx = driving_gear.center.x - driven_gear.center.x
        dy = driving_gear.center.y - driven_gear.center.y
        actual_distance = math.sqrt(dx*dx + dy*dy)
        
        # Required distance for proper meshing
        required_distance = driving_radius + driven_radius
        
        return abs(actual_distance - required_distance) <= tolerance
    
    def get_optimal_center_distance(self, driving_teeth: int, driven_teeth: int) -> float:
        """
        Calculate optimal center distance for meshing.
        
        Args:
            driving_teeth: Teeth count of driving gear
            driven_teeth: Teeth count of driven gear
            
        Returns:
            Optimal center distance
        """
        driving_radius = (self.module * driving_teeth) / 2.0
        driven_radius = (self.module * driven_teeth) / 2.0
        return driving_radius + driven_radius
    
    def validate_tooth_count_compatibility(self, teeth1: int, teeth2: int, 
                                         min_ratio: float = 0.2, max_ratio: float = 5.0) -> bool:
        """
        Validate that tooth counts are compatible for meshing.
        
        Args:
            teeth1: First gear teeth count
            teeth2: Second gear teeth count
            min_ratio: Minimum acceptable ratio
            max_ratio: Maximum acceptable ratio
            
        Returns:
            True if compatible, False otherwise
        """
        ratio = teeth1 / teeth2 if teeth2 != 0 else float('inf')
        return min_ratio <= ratio <= max_ratio
    
    def find_valid_meshing_positions(self, fixed_gear: Gear, candidate_teeth: int, 
                                   boundary_points: List, constraints: Dict) -> List[tuple]:
        """
        Find valid positions for a gear to mesh with a fixed gear.
        
        Args:
            fixed_gear: Already placed gear
            candidate_teeth: Teeth count for new gear
            boundary_points: Boundary polygon points
            constraints: System constraints
            
        Returns:
            List of valid (x, y) positions
        """
        # Calculate required distance
        fixed_driving_teeth = fixed_gear.teeth_count[-1]  # Last element drives next gear
        required_distance = self.get_optimal_center_distance(fixed_driving_teeth, candidate_teeth)
        
        # Sample positions around the fixed gear at required distance
        valid_positions = []
        for angle_deg in range(0, 360, 10):  # Sample every 10 degrees
            angle_rad = math.radians(angle_deg)
            candidate_x = fixed_gear.center.x + required_distance * math.cos(angle_rad)
            candidate_y = fixed_gear.center.y + required_distance * math.sin(angle_rad)
            
            # Check if position is valid within boundary
            candidate_center = type('Point', (), {'x': candidate_x, 'y': candidate_y})
            if self._is_position_valid(candidate_center, boundary_points, constraints):
                valid_positions.append((candidate_x, candidate_y))
                
        return valid_positions
    
    def _is_position_valid(self, center, boundary_points, constraints):
        """Check if a position is valid within boundary constraints."""
        # Simple boundary check - should use proper polygon containment
        boundary_x = [p.x for p in boundary_points]
        boundary_y = [p.y for p in boundary_points]
        
        margin = constraints.get('boundary_margin', 1.0)
        min_x, max_x = min(boundary_x), max(boundary_x)
        min_y, max_y = min(boundary_y), max(boundary_y)
        
        return (min_x + margin <= center.x <= max_x - margin and 
                min_y + margin <= center.y <= max_y - margin)