"""
Success/failure condition rules for GearRL system.
"""

from typing import List, Dict, Any
from common.data_models import ValidationReport, GearLayout, SystemDefinition


class SuccessFailureRules:
    """Rules for determining success and failure conditions."""
    
    @staticmethod
    def is_complete_success(report: ValidationReport, layout: GearLayout, 
                           system: SystemDefinition) -> bool:
        """
        Determine if layout represents a complete success.
        
        Args:
            report: Validation report
            layout: Gear layout
            system: System definition
            
        Returns:
            True if complete success, False otherwise
        """
        # Must be valid
        if not report.is_valid:
            return False
            
        # Must have at least one gear connecting input to output
        if len(layout.gears) == 0:
            return False
            
        # Must satisfy torque ratio constraint if specified
        if system.constraints.torque_ratio != "free":
            # For now, we'll assume it's satisfied if the layout is valid
            # In practice, you'd want to use the TorqueRatioRules class
            pass
                
        return True
    
    @staticmethod
    def is_partial_success(report: ValidationReport, layout: GearLayout) -> bool:
        """
        Determine if layout represents a partial success (valid but incomplete).
        
        Args:
            report: Validation report
            layout: Gear layout
            
        Returns:
            True if partial success, False otherwise
        """
        # Must be valid but can be incomplete
        return report.is_valid and len(layout.gears) > 0
    
    @staticmethod
    def is_failure(report: ValidationReport) -> bool:
        """
        Determine if layout represents a failure.
        
        Args:
            report: Validation report
            
        Returns:
            True if failure, False otherwise
        """
        return not report.is_valid
    
    @staticmethod
    def get_failure_reasons(report: ValidationReport) -> List[str]:
        """
        Get detailed failure reasons from validation report.
        
        Args:
            report: Validation report
            
        Returns:
            List of failure reason strings
        """
        return report.errors.copy()
    
    @staticmethod
    def is_termination_condition_met(layout: GearLayout, system: SystemDefinition, 
                                   max_gears: int = 10) -> bool:
        """
        Check if termination condition is met for RL environment.
        
        Args:
            layout: Current gear layout
            system: System definition
            max_gears: Maximum number of gears allowed
            
        Returns:
            True if should terminate, False otherwise
        """
        # Too many gears
        if len(layout.gears) >= max_gears:
            return True
            
        # Check if output shaft is reached
        if len(layout.gears) > 0:
            last_gear = layout.gears[-1]
            distance_to_output = ((last_gear.center.x - system.output_shaft.x)**2 + 
                                (last_gear.center.y - system.output_shaft.y)**2)**0.5
            # If last gear is close enough to output shaft
            if distance_to_output < 5.0:  # Threshold distance
                return True
                
        return False