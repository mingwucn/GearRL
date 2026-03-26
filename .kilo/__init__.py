"""
GearRL Reusable Skills and Rules Package

This package provides reusable components for the GearRL system.
All skills and rules are designed to be modular, composable, and easy to integrate.

Usage:
    import sys
    sys.path.append('.kilo')
    
    # Import skills
    from kilo.skills import DataModelSkill, GearGenerator, PhysicsValidationSkill
    
    # Import rules  
    from kilo.rules import ConstraintValidationRules, TorqueRatioRules

For detailed usage documentation, see .kilo/USAGE_GUIDE.md
"""

# Skills imports
from .skills.data_model_skills import DataModelSkill, CoordinateTransformer, SystemValidator
from .skills.gear_generation_skills import GearGenerator
from .skills.pathfinding_skills import PathfinderSkill
from .skills.physics_validation_skills import PhysicsValidationSkill
from .skills.preprocessing_skills import ImageProcessor
from .skills.rl_environment_skills import StateRepresentationSkill
from .skills.visualization_skills import VisualizationSkill
from .skills.utility_skills import GeometryUtils, MathUtils, FileUtils

# Rules imports  
from .rules.constraint_validation_rules import ConstraintValidationRules
from .rules.gear_placement_rules import GearPlacementRules
from .rules.meshing_compatibility_rules import MeshingCompatibilityRules
from .rules.boundary_margin_rules import BoundaryMarginRules
from .rules.torque_ratio_rules import TorqueRatioRules
from .rules.success_failure_rules import SuccessFailureRules

__all__ = [
    # Skills
    'DataModelSkill',
    'CoordinateTransformer', 
    'SystemValidator',
    'GearGenerator',
    'PathfinderSkill',
    'PhysicsValidationSkill',
    'ImageProcessor',
    'StateRepresentationSkill',
    'VisualizationSkill',
    'GeometryUtils',
    'MathUtils', 
    'FileUtils',
    
    # Rules
    'ConstraintValidationRules',
    'GearPlacementRules',
    'MeshingCompatibilityRules', 
    'BoundaryMarginRules',
    'TorqueRatioRules',
    'SuccessFailureRules'
]
