#!/usr/bin/env python3
import sys
import json
from pathlib import Path

sys.path.append('.')

from common.data_models import GearLayout, SystemDefinition, Boundary, Point, Constraints
from physics_validator.validator import PhysicsValidator

def main():
    layout_path = sys.argv[1]
    constraints_path = sys.argv[2]
    
    # Load layout
    with open(layout_path, 'r') as f:
        layout_data = json.load(f)
    layout = GearLayout.from_json(layout_data)
    
    # Load constraints and create system definition
    with open(constraints_path, 'r') as f:
        constraints_data = json.load(f)
    
    # Extract example name to get processed data
    example_name = Path(constraints_path).stem.replace('_constraints', '')
    processed_path = f"data/intermediate/{example_name}_processed.json"
    
    with open(processed_path, 'r') as f:
        processed_data = json.load(f)['normalized_space']
    
    system = SystemDefinition(
        boundary=Boundary(points=[Point(p[0], p[1]) for p in processed_data['boundaries']]),
        input_shaft=Point(processed_data['input_shaft']['x'], processed_data['input_shaft']['y']),
        output_shaft=Point(processed_data['output_shaft']['x'], processed_data['output_shaft']['y']),
        constraints=Constraints.from_json(constraints_data)
    )
    
    # Validate
    validator = PhysicsValidator()
    report = validator.check_layout(layout, system)
    
    print(f"✅ Layout is valid: {report.is_valid}")
    if not report.is_valid:
        print("❌ Validation errors:")
        for error in report.errors:
            print(f"   - {error}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
