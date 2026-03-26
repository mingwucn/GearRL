#!/usr/bin/env python3
"""
Debug script to test gear creation and access.
"""

import sys
sys.path.append('.')

from geometry_env.simulator import GearTrainSimulator
from gear_generator.factory import GearFactory
from pathfinding.finder import Pathfinder

def debug_gear_creation():
    """Debug gear creation and center access."""
    
    # Load Example1 data
    with open('data/intermediate/Example1_processed.json', 'r') as f:
        data = json.load(f)['normalized_space']
    
    # Run pathfinding
    pathfinder = Pathfinder()
    optimal_path = pathfinder.find_path('data/intermediate/Example1_processed.json')
    print(f"Path length: {len(optimal_path)}")
    
    # Create simulator
    gear_factory = GearFactory(module=1.0)
    simulator = GearTrainSimulator(
        path=optimal_path,
        input_shaft=(data['input_shaft']['x'], data['input_shaft']['y']),
        output_shaft=(data['output_shaft']['x'], data['output_shaft']['y']),
        boundaries=data['boundaries'],
        gear_factory=gear_factory,
        clearance_margin=2.0
    )
    
    # Reset simulator
    state, reward, done, info = simulator.reset(initial_gear_teeth=20)
    print(f"Reset done: {done}, info: {info}")
    print(f"Number of gears: {len(simulator.gears)}")
    
    # Check gear types and centers
    for i, gear in enumerate(simulator.gears):
        print(f"Gear {i}: type={type(gear).__name__}")
        print(f"  center type: {type(gear.center)}")
        print(f"  center: {gear.center}")
        if hasattr(gear.center, 'x'):
            print(f"  center.x: {gear.center.x}")
        else:
            print(f"  center[0]: {gear.center[0]}")

if __name__ == "__main__":
    import json
    debug_gear_creation()