#!/usr/bin/env python3
"""
Direct test of fixed components without RL dependencies.
"""

import sys
import os
import json

sys.path.append('.')

from geometry_env.fixed_env import FixedGearEnv
from physics_validator.fixed_validator import FixedPhysicsValidator
from common.data_models import GearLayout, Gear, Point

def test_fixed_physics_validator():
    """Test FixedPhysicsValidator with Example1 constraints."""
    print("Testing FixedPhysicsValidator...")
    
    # Load Example1 constraints
    with open('data/Example1_constraints.json', 'r') as f:
        constraint_data = json.load(f)
    
    # Create valid gear layout for testing
    gears = [
        Gear(id="0", center=Point(36.31, 1.53), teeth_count=[20], module=1.0),
        Gear(id="1", center=Point(-32.08, 11.06), teeth_count=[40], module=1.0)
    ]
    layout = GearLayout(gears=gears)
    
    # Load system definition
    with open('data/intermediate/Example1_processed.json', 'r') as f:
        data = json.load(f)['normalized_space']
    
    from common.data_models import SystemDefinition, Boundary, Constraints
    
    system_definition = SystemDefinition(
        boundary=Boundary(points=[Point(p[0], p[1]) for p in data['boundaries']]),
        input_shaft=Point(data['input_shaft']['x'], data['input_shaft']['y']),
        output_shaft=Point(data['output_shaft']['x'], data['output_shaft']['y']),
        constraints=Constraints.from_json(constraint_data)
    )
    
    # Validate
    validator = FixedPhysicsValidator()
    report = validator.check_layout(layout, system_definition)
    
    print(f"Validation result: {report.is_valid}")
    if not report.is_valid:
        for error in report.errors:
            print(f"  Error: {error}")
    else:
        print("✅ Validation passed!")
    
    return report.is_valid

def test_fixed_gear_env_initialization():
    """Test FixedGearEnv initialization."""
    print("\nTesting FixedGearEnv initialization...")
    
    try:
        env = FixedGearEnv({'json_path': 'data/intermediate/Example1_processed.json'})
        print("✅ Environment initialized successfully")
        env.close()
        return True
    except Exception as e:
        print(f"❌ Environment initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("🔬 Testing Fixed Components")
    print("=" * 40)
    
    validator_ok = test_fixed_physics_validator()
    env_ok = test_fixed_gear_env_initialization()
    
    print("\n" + "=" * 40)
    if validator_ok and env_ok:
        print("✅ All fixed components working correctly!")
    else:
        print("❌ Some components have issues")