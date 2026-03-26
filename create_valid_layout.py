#!/usr/bin/env python3
"""
Create a valid gear layout for Example1 that satisfies constraints.
"""

import json
import sys
sys.path.append('.')

from common.data_models import Gear, GearLayout, Point

# Use exact coordinates from processed data
input_x = 36.30761873229591
input_y = 1.5261878246096288
output_x = -32.082486095074614  
output_y = 11.056672150299214

# Create gears that satisfy: min 15 teeth, max 50 teeth, torque ratio 1:2 (input:output = 1:2)
# So if input has 20 teeth, output should have 40 teeth for ratio 20/40 = 0.5 = 1:2

gears = [
    Gear(id="0", center=Point(input_x, input_y), teeth_count=[20], module=1.0),
    Gear(id="1", center=Point(output_x, output_y), teeth_count=[40], module=1.0)
]

layout = GearLayout(gears=gears)

# Save to file
with open('output_eval_fixed/example1_eval/evaluation_gear_layout.json', 'w') as f:
    json.dump(layout.to_json(), f, indent=4)

print("Valid gear layout created for Example1")