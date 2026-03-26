#!/usr/bin/env python3
"""
Validate the manually created layout using FixedPhysicsValidator.
"""

import json
import sys
sys.path.append('.')

from physics_validator.fixed_validator import FixedPhysicsValidator
from common.data_models import GearLayout, SystemDefinition, Boundary, Point, Constraints

def validate_manual_layout():
    # Load layout
    with open('output_eval_fixed/example1_eval/evaluation_gear_layout.json', 'r') as f:
        layout_data = json.load(f)
    layout = GearLayout.from_json(layout_data)
    
    # Load system definition
    with open('data/intermediate/Example1_processed.json', 'r') as f:
        data = json.load(f)['normalized_space']
    
    with open('data/Example1_constraints.json', 'r') as f:
        constraint_data = json.load(f)
    
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
        print("✅ Manual layout is scientifically valid!")
    
    # Save validation report
    with open('output_eval_fixed/example1_eval/validation_report.json', 'w') as f:
        json.dump(report.to_json(), f, indent=4)
    
    return report.is_valid

if __name__ == "__main__":
    validate_manual_layout()