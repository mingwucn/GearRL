#!/usr/bin/env python3
"""
Calculate maximum possible gear sizes for Example1 shafts.
"""

import sys
import json
sys.path.append('.')

from physics_validator.fixed_validator import FixedPhysicsValidator

def calculate_max_gear_sizes():
    # Load system data
    with open('data/intermediate/Example1_processed.json', 'r') as f:
        data = json.load(f)['normalized_space']

    with open('data/Example1_constraints.json', 'r') as f:
        constraint_data = json.load(f)
    
    from common.data_models import Point

    boundary_points = [Point(p[0], p[1]) for p in data['boundaries']]
    input_shaft = Point(data['input_shaft']['x'], data['input_shaft']['y'])
    output_shaft = Point(data['output_shaft']['x'], data['output_shaft']['y'])
    
    margin = constraint_data['boundary_margin']
    
    # Calculate min distance to boundary for each shaft
    min_dist_input = FixedPhysicsValidator._min_distance_to_boundary(input_shaft, boundary_points)
    min_dist_output = FixedPhysicsValidator._min_distance_to_boundary(output_shaft, boundary_points)
    
    print(f"Input shaft min distance to boundary: {min_dist_input:.4f}")
    print(f"Output shaft min distance to boundary: {min_dist_output:.4f}")
    
    # Max radius = min_dist - margin
    max_radius_input = min_dist_input - margin
    max_radius_output = min_dist_output - margin
    
    print(f"Max radius at input (with margin): {max_radius_input:.4f}")
    print(f"Max radius at output (with margin): {max_radius_output:.4f}")
    
    # Convert to teeth count (module=1.0, so diameter = teeth, radius = teeth/2)
    max_teeth_input = int(max_radius_input * 2)
    max_teeth_output = int(max_radius_output * 2)
    
    print(f"Max teeth at input: {max_teeth_input}")
    print(f"Max teeth at output: {max_teeth_output}")
    
    # Check if torque ratio 1:2 is possible
    if max_teeth_input >= 15 and max_teeth_output >= 15:
        # Can we achieve ratio 0.5?
        # input_teeth / output_teeth = 0.5 => output_teeth = 2 * input_teeth
        # So we need: input_teeth <= max_teeth_input AND 2*input_teeth <= max_teeth_output
        max_input_for_ratio = min(max_teeth_input, max_teeth_output // 2)
        if max_input_for_ratio >= 15:
            print(f"✅ Torque ratio 1:2 IS achievable with input={max_input_for_ratio}, output={2*max_input_for_ratio}")
        else:
            print(f"❌ Torque ratio 1:2 NOT achievable. Max input for ratio: {max_input_for_ratio} (<15)")
    else:
        print("❌ Shaft positions don't allow minimum gear size of 15")

if __name__ == "__main__":
    calculate_max_gear_sizes()
