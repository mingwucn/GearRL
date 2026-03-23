"""
RL environment skills for GearRL system handling state representation and reward shaping.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from common.data_models import GearLayout, SystemDefinition, ValidationReport, Gear, Point


class StateRepresentationSkill:
    """Handles state representation for RL environments."""
    
    def __init__(self, config: Dict[str, Any]):
        self.min_teeth = config.get("min_gear_teeth", 8)
        self.max_teeth = config.get("max_gear_teeth", 40)
        self.observation_size = 5  # [last_gear_x, last_gear_y, last_gear_teeth, last_gear_radius, dist_to_target]
    
    def get_initial_observation(self, system: SystemDefinition) -> np.ndarray:
        """Get initial observation state."""
        return np.array([
            system.input_shaft.x,
            system.input_shaft.y,
            float(self.min_teeth + (self.max_teeth - self.min_teeth) // 2),  # middle teeth count
            0.0,  # initial radius
            self._distance(system.input_shaft, system.output_shaft)
        ], dtype=np.float32)
    
    def get_observation_from_layout(self, layout: GearLayout, system: SystemDefinition) -> np.ndarray:
        """Convert gear layout to observation vector."""
        if not layout.gears:
            return self.get_initial_observation(system)
            
        last_gear = layout.gears[-1]
        last_teeth = last_gear.teeth_count[-1]  # driving teeth count
        last_radius = last_gear.diameters[-1] / 2.0
        dist_to_target = self._distance(last_gear.center, system.output_shaft)
        
        return np.array([
            last_gear.center.x,
            last_gear.center.y,
            float(last_teeth),
            last_radius,
            dist_to_target
        ], dtype=np.float32)
    
    def _distance(self, p1: Point, p2: Point) -> float:
        """Calculate Euclidean distance between two points."""
        return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2)**0.5


class RewardShapingSkill:
    """Handles reward calculation and shaping for RL training."""
    
    def __init__(self, config: Dict[str, Any]):
        self.torque_weight = config.get("torque_weight", 1.0)
        self.space_weight = config.get("space_weight", 0.5)
        self.weight_penalty_coef = config.get("weight_penalty_coef", 0.1)
        self.invalid_penalty = config.get("invalid_penalty", -10.0)
    
    def calculate_reward(self, report: ValidationReport, layout: GearLayout, 
                        system: SystemDefinition, target_torque: Optional[float] = None) -> float:
        """
        Calculate reward based on validation report and layout metrics.
        
        Args:
            report: Validation report from physics validator
            layout: Current gear layout
            system: System definition with constraints
            target_torque: Desired torque ratio (if applicable)
            
        Returns:
            Calculated reward scalar
        """
        # Heavy penalty for invalid designs
        if not report.is_valid:
            return self.invalid_penalty
        
        # Calculate torque reward if target specified
        torque_reward = 0.0
        if target_torque is not None:
            actual_ratio = self._calculate_actual_torque_ratio(layout, system)
            if actual_ratio is not None:
                torque_diff = abs(actual_ratio - target_torque)
                torque_reward = self.torque_weight * np.exp(-torque_diff)
        
        # Calculate space usage reward (encourage compact designs)
        space_usage = self._calculate_space_usage(layout, system)
        space_reward = self.space_weight * space_usage
        
        # Calculate weight penalty (discourage large/heavy gears)
        weight_penalty = self.weight_penalty_coef * self._calculate_total_mass(layout)
        
        return torque_reward + space_reward - weight_penalty
    
    def _calculate_actual_torque_ratio(self, layout: GearLayout, system: SystemDefinition) -> Optional[float]:
        """Calculate actual torque ratio from gear layout."""
        if len(layout.gears) < 2:
            return None
            
        # Find input and output gears (nearest to shafts)
        input_gear = min(layout.gears, key=lambda g: 
            ((g.center.x - system.input_shaft.x)**2 + (g.center.y - system.input_shaft.y)**2)**0.5)
        output_gear = min(layout.gears, key=lambda g: 
            ((g.center.x - system.output_shaft.x)**2 + (g.center.y - system.output_shaft.y)**2)**0.5)
            
        if input_gear is output_gear:
            return None
            
        return input_gear.teeth_count[0] / output_gear.teeth_count[0]
    
    def _calculate_space_usage(self, layout: GearLayout, system: SystemDefinition) -> float:
        """Calculate space usage efficiency (higher = better utilization)."""
        if not layout.gears:
            return 0.0
            
        # Get bounding box of all gears
        all_x = []
        all_y = []
        for gear in layout.gears:
            all_x.append(gear.center.x)
            all_y.append(gear.center.y)
            # Add gear radii to account for full extent
            max_radius = max(d / 2.0 for d in gear.diameters)
            all_x.extend([gear.center.x - max_radius, gear.center.x + max_radius])
            all_y.extend([gear.center.y - max_radius, gear.center.y + max_radius])
        
        gear_width = max(all_x) - min(all_x)
        gear_height = max(all_y) - min(all_y)
        gear_area = gear_width * gear_height
        
        # Get boundary area
        boundary_x = [p.x for p in system.boundary.points]
        boundary_y = [p.y for p in system.boundary.points]
        boundary_width = max(boundary_x) - min(boundary_x)
        boundary_height = max(boundary_y) - min(boundary_y)
        boundary_area = boundary_width * boundary_height
        
        if boundary_area == 0:
            return 0.0
            
        return min(1.0, gear_area / boundary_area)
    
    def _calculate_total_mass(self, layout: GearLayout) -> float:
        """Calculate approximate total mass of gear layout."""
        total_mass = 0.0
        for gear in layout.gears:
            # Approximate mass as sum of areas of all gear circles
            for diameter in gear.diameters:
                radius = diameter / 2.0
                area = np.pi * radius**2
                total_mass += area
        return total_mass