"""
Torque ratio rules for GearRL system.
"""

from typing import List, Dict, Any, Optional
import math
from common.data_models import GearLayout, SystemDefinition, Gear


class TorqueRatioRules:
    """Rules for torque ratio calculation and validation."""
    
    @staticmethod
    def calculate_actual_torque_ratio(layout: GearLayout, system: SystemDefinition) -> float:
        """
        Calculate actual torque ratio from gear layout.
        
        Args:
            layout: Current gear layout
            system: System definition with shaft positions
            
        Returns:
            Actual torque ratio (input/output)
        """
        if len(layout.gears) < 1:
            return 1.0
            
        # Find input and output gears (nearest to shafts)
        input_gear = min(layout.gears, key=lambda g: 
            ((g.center.x - system.input_shaft.x)**2 + (g.center.y - system.input_shaft.y)**2)**0.5)
        output_gear = min(layout.gears, key=lambda g: 
            ((g.center.x - system.output_shaft.x)**2 + (g.center.y - system.output_shaft.y)**2)**0.5)
            
        input_teeth = input_gear.teeth_count[0]  # Driven teeth count
        output_teeth = output_gear.teeth_count[-1]  # Driving teeth count
        
        if output_teeth == 0:
            return float('inf')
            
        return input_teeth / output_teeth
    
    @staticmethod
    def parse_target_torque_ratio(target_str: str) -> Optional[float]:
        """
        Parse target torque ratio string.
        
        Args:
            target_str: Torque ratio string (e.g., "2:1", "1:3", "free")
            
        Returns:
            Target torque ratio as float, or None if "free"
        """
        if target_str == "free":
            return None
            
        try:
            parts = target_str.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid torque ratio format")
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            raise ValueError(f"Invalid torque ratio format: {target_str}")
    
    @staticmethod
    def validate_torque_ratio(actual_ratio: float, target_ratio: Optional[float], 
                            tolerance: float = 0.05) -> bool:
        """
        Validate that actual torque ratio matches target within tolerance.
        
        Args:
            actual_ratio: Actual calculated torque ratio
            target_ratio: Target torque ratio
            tolerance: Relative tolerance (e.g., 0.05 = 5%)
            
        Returns:
            True if within tolerance, False otherwise
        """
        if target_ratio is None:  # "free" mode
            return True
            
        if target_ratio == 0:
            return actual_ratio == 0
            
        relative_error = abs(actual_ratio - target_ratio) / target_ratio
        return relative_error <= tolerance
    
    @staticmethod
    def calculate_compound_gear_ratio(gear_train: List[Gear]) -> float:
        """
        Calculate overall ratio for a compound gear train.
        
        Args:
            gear_train: Ordered list of gears in the train
            
        Returns:
            Overall torque ratio
        """
        if len(gear_train) < 2:
            return 1.0
            
        overall_ratio = 1.0
        for i in range(len(gear_train) - 1):
            driving_teeth = gear_train[i].teeth_count[-1]   # Last element drives next
            driven_teeth = gear_train[i + 1].teeth_count[0]  # First element is driven
            stage_ratio = driven_teeth / driving_teeth
            overall_ratio *= stage_ratio
            
        return overall_ratio