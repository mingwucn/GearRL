#!/usr/bin/env python3
"""
Simple example usage of the .kilo reusable skills and rules package.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.kilo'))

from skills.data_model_skills import DataModelSkill
from skills.gear_generation_skills import GearGenerator  
from skills.utility_skills import GeometryUtils, MathUtils
from common.data_models import Point


def main():
    """Demonstrate .kilo package usage."""
    
    print("🔧 Demonstrating .kilo Reusable Skills and Rules")
    print("=" * 50)
    
    # 1. Use utility functions
    print("\n1. Utility Functions:")
    p1 = Point(0, 0)
    p2 = Point(3, 4)
    distance = GeometryUtils.distance(p1, p2)
    print(f"   Distance between points: {distance}")
    
    clamped_value = MathUtils.clamp(150, 0, 100)
    print(f"   Clamped value (150 -> 0-100): {clamped_value}")
    
    # 2. Use gear generation skills
    print("\n2. Gear Generation:")
    generator = GearGenerator(module=1.0)
    
    simple_gear = generator.create_simple_gear(
        gear_id="input", 
        center=Point(10, 20), 
        teeth_count=25
    )
    print(f"   Created simple gear: {simple_gear.teeth_count[0]} teeth")
    
    # 3. Use data model skills
    print("\n3. Data Model Operations:")
    from common.data_models import SystemDefinition, Boundary, Constraints
    
    boundary = Boundary(points=[Point(-50, -50), Point(50, -50), Point(50, 50), Point(-50, 50)])
    constraints = Constraints(torque_ratio="1:2", mass_space_ratio=0.7, boundary_margin=5.0, min_gear_size=15, max_gear_size=50)
    system = SystemDefinition(
        boundary=boundary,
        input_shaft=Point(-40, 0),
        output_shaft=Point(40, 0),
        constraints=constraints
    )
    
    # Serialize system
    serialized_system = DataModelSkill.serialize_system_definition(system)
    print(f"   Serialized system: {len(str(serialized_system))} characters")
    
    print("\n✅ Example completed successfully!")
    print("\n📚 For detailed usage documentation, see .kilo/USAGE_GUIDE.md")


if __name__ == "__main__":
    main()
