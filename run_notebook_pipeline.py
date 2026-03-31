#!/usr/bin/env python3
"""
Run the GearRL pipeline with delta volume reasoning and generate visualized results.
This script replicates the Jupyter notebook functionality in a more reliable way.
"""

import sys
import os
import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# Add project root and .kilo to path
project_root = Path.cwd()
sys.path.append(str(project_root))
sys.path.append(str(project_root / '.kilo'))

# Import skills
from skills.preprocessing_skills import ImageProcessor
from skills.pathfinding_skills import AStarPathfinder  # Fixed class name
from skills.gear_generation_skills import GearGenerator
from skills.physics_validation_skills import PhysicsValidationSkill
from skills.data_model_skills import DataModelSkill, CoordinateTransformer
from skills.visualization_skills import VisualizationSkill
from skills.utility_skills import GeometryUtils, MathUtils

# Import rules
from rules.constraint_validation_rules import ConstraintValidationRules
from rules.torque_ratio_rules import TorqueRatioRules
from rules.boundary_margin_rules import BoundaryMarginRules
from common.data_models import SystemDefinition, Boundary, Point, Constraints, GearLayout

print("✅ Project paths configured")
print("✅ Skills and rules imported successfully")

def load_example_data(example_name="Example1"):
    """Load example data including constraints and processed data."""
    
    # Load constraints
    constraints_path = f"data/{example_name}_constraints.json"
    with open(constraints_path, 'r') as f:
        constraints = json.load(f)
    
    # Load processed data
    processed_path = f"data/intermediate/{example_name}_processed.json"
    with open(processed_path, 'r') as f:
        processed_data = json.load(f)
    
    print(f"Loaded {example_name}:")
    print(f"  - Torque ratio: {constraints['torque_ratio']}")
    print(f"  - Min gear size: {constraints['min_gear_size']}")
    print(f"  - Max gear size: {constraints['max_gear_size']}")
    print(f"  - Boundary margin: {constraints['boundary_margin']}")
    
    return constraints, processed_data

class DeltaVolumeReasoner:
    """Implements delta volume reasoning for gear train optimization."""
    
    def __init__(self, module=1.0):
        self.module = module
        
    def calculate_gear_volume(self, teeth_count):
        """Calculate gear volume based on teeth count (simplified as area)."""
        diameter = teeth_count * self.module
        radius = diameter / 2
        return np.pi * radius ** 2
    
    def optimize_gear_sizes_for_volume(self, min_teeth, max_teeth, target_torque_ratio, input_gear_teeth):
        """Optimize gear sizes to minimize volume while meeting torque ratio."""
        best_teeth = None
        min_volume = float('inf')
        
        # Parse target torque ratio
        ratio_parts = target_torque_ratio.split(":")
        if len(ratio_parts) == 2:
            target_input_to_output = float(ratio_parts[0]) / float(ratio_parts[1])
        else:
            target_input_to_output = 1.0
        
        # Expected output gear teeth based on input
        expected_output_teeth = input_gear_teeth / target_input_to_output
        
        # Search for optimal intermediate gears
        for driven_teeth in range(min_teeth, max_teeth + 1):
            for driving_teeth in range(min_teeth, max_teeth + 1):
                # Check if this combination can achieve the target
                actual_ratio = (input_gear_teeth / driven_teeth) * (driving_teeth / expected_output_teeth)
                
                if MathUtils.is_close(actual_ratio, 1.0, rel_tol=0.05):  # Within 5% tolerance
                    volume = (self.calculate_gear_volume(driven_teeth) + 
                             self.calculate_gear_volume(driving_teeth))
                    
                    if volume < min_volume:
                        min_volume = volume
                        best_teeth = (driven_teeth, driving_teeth)
        
        return best_teeth, min_volume

def main():
    """Run the complete GearRL pipeline."""
    
    # Load example data
    example_name = "Example1"
    constraints, processed_data = load_example_data(example_name)
    
    # Preprocessing
    normalized_data = processed_data['normalized_space']
    boundaries = normalized_data['boundaries']
    input_shaft = normalized_data['input_shaft']
    output_shaft = normalized_data['output_shaft']
    
    print("✅ Preprocessing completed")
    print(f"  - Boundary points: {len(boundaries)}")
    print(f"  - Input shaft: ({input_shaft['x']:.2f}, {input_shaft['y']:.2f})")
    print(f"  - Output shaft: ({output_shaft['x']:.2f}, {output_shaft['y']:.2f})")
    
    # Pathfinding
    pathfinder = AStarPathfinder()
    
    # Create temporary file for pathfinding
    temp_processed_path = f"temp_{example_name}_processed.json"
    with open(temp_processed_path, 'w') as f:
        json.dump({"normalized_space": normalized_data}, f)
    
    # Find centerline path
    try:
        path = pathfinder.find_centerline_path(
            temp_processed_path, 
            step_size=0.5, 
            smoothing_iterations=100
        )
        
        if path:
            print(f"✅ Pathfinding successful: {len(path)} points")
            path_length = sum(
                GeometryUtils.distance(Point(path[i][0], path[i][1]), Point(path[i+1][0], path[i+1][1]))
                for i in range(len(path)-1)
            )
            print(f"  - Path length: {path_length:.2f}")
        else:
            print("⚠️  Pathfinding failed, using straight line")
            path = [[input_shaft['x'], input_shaft['y']], [output_shaft['x'], output_shaft['y']]]
            
    except Exception as e:
        print(f"⚠️  Pathfinding error: {e}")
        path = [[input_shaft['x'], input_shaft['y']], [output_shaft['x'], output_shaft['y']]]
    
    # Clean up temp file
    if os.path.exists(temp_processed_path):
        os.remove(temp_processed_path)
    
    # Delta Volume Reasoning
    volume_reasoner = DeltaVolumeReasoner(module=1.0)
    input_gear_teeth = constraints['min_gear_size'] + 5  # Start with reasonable size
    output_gear_teeth = int(input_gear_teeth / 2)  # For 1:2 ratio
    
    print("✅ Delta Volume Reasoning initialized")
    print(f"  - Input gear teeth: {input_gear_teeth}")
    print(f"  - Output gear teeth: {output_gear_teeth}")
    print(f"  - Target torque ratio: {constraints['torque_ratio']}")
    
    # Gear Generation
    generator = GearGenerator(module=1.0)
    
    # Create input and output gears
    input_gear = generator.create_simple_gear(
        gear_id="gear_input",
        center=Point(input_shaft['x'], input_shaft['y']),
        teeth_count=input_gear_teeth
    )
    
    output_gear = generator.create_simple_gear(
        gear_id="gear_output", 
        center=Point(output_shaft['x'], output_shaft['y']),
        teeth_count=output_gear_teeth
    )
    
    # Optimize intermediate gears using delta volume reasoning
    optimal_teeth, min_volume = volume_reasoner.optimize_gear_sizes_for_volume(
        min_teeth=constraints['min_gear_size'],
        max_teeth=constraints['max_gear_size'],
        target_torque_ratio=constraints['torque_ratio'],
        input_gear_teeth=input_gear_teeth
    )
    
    if optimal_teeth:
        driven_teeth, driving_teeth = optimal_teeth
        
        # Calculate intermediate gear position (midpoint of path)
        path_midpoint = len(path) // 2
        mid_x = path[path_midpoint][0]
        mid_y = path[path_midpoint][1]
        
        intermediate_gear = generator.create_compound_gear(
            "gear_intermediate",
            Point(mid_x, mid_y),
            [driven_teeth, driving_teeth]
        )
        
        gears = [input_gear, intermediate_gear, output_gear]
        print(f"✅ Intermediate gears optimized: {driven_teeth} → {driving_teeth} teeth")
        print(f"  - Minimized volume: {min_volume:.2f}")
    else:
        gears = [input_gear, output_gear]
        print("⚠️  No optimal intermediate gears found, using direct connection")
    
    print(f"✅ Generated {len(gears)} gears")
    
    # Physics Validation
    boundary_points = [Point(p[0], p[1]) for p in boundaries]
    system_definition = SystemDefinition(
        boundary=Boundary(points=boundary_points),
        input_shaft=Point(input_shaft['x'], input_shaft['y']),
        output_shaft=Point(output_shaft['x'], output_shaft['y']),
        constraints=Constraints.from_json(constraints)
    )
    
    gear_layout = GearLayout(gears=gears)
    
    validator = PhysicsValidationSkill()
    validation_report = validator.validate_layout(gear_layout, system_definition)
    
    print(f"✅ Physics Validation completed")
    print(f"  - Layout is valid: {validation_report.is_valid}")
    if not validation_report.is_valid:
        print("  - Validation errors:")
        for i, error in enumerate(validation_report.errors[:3]):  # Show first 3 errors
            print(f"    {i+1}. {error}")
    
    # Visualization
    viz = VisualizationSkill(figsize=(15, 10), dpi=150)
    
    # Create output directory
    output_dir = Path("notebook_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Save gear layout
    layout_path = output_dir / f"{example_name}_notebook_layout.json"
    with open(layout_path, 'w') as f:
        json.dump([g.to_json() for g in gears], f, indent=2)
    
    # Convert path to Point objects for visualization
    path_points = [Point(p[0], p[1]) for p in path]
    
    # Create visualization
    viz_output_path = output_dir / f"{example_name}_notebook_result.png"
    viz.render_system(system_definition, str(viz_output_path), path_points, gears)
    
    print(f"✅ Visualization saved to: {viz_output_path}")
    
    # Results Summary
    total_teeth = sum(gear.teeth_count[0] for gear in gears)
    total_volume = sum(volume_reasoner.calculate_gear_volume(gear.teeth_count[0]) for gear in gears)
    
    actual_torque_ratio = TorqueRatioRules.calculate_actual_torque_ratio(gear_layout, system_definition)
    target_torque_ratio = TorqueRatioRules.parse_target_torque_ratio(constraints['torque_ratio'])
    torque_error = abs(actual_torque_ratio - target_torque_ratio) / target_torque_ratio * 100 if target_torque_ratio else 0
    
    print("# 📊 Final Results Summary")
    print(f"## {example_name}")
    print(f"- **Status**: {'✅ VALID' if validation_report.is_valid else '❌ INVALID'}")
    print(f"- **Gears Generated**: {len(gears)}")
    print(f"- **Total Teeth**: {total_teeth}")
    print(f"- **Total Volume**: {total_volume:.2f}")
    print(f"- **Target Torque Ratio**: {target_torque_ratio:.2f}" if target_torque_ratio else "- **Target Torque Ratio**: free")
    print(f"- **Actual Torque Ratio**: {actual_torque_ratio:.2f}")
    print(f"- **Torque Error**: {torque_error:.1f}%")
    print(f"- **Delta Volume Optimization**: {'Applied' if optimal_teeth else 'Not Applied'}")
    
    # Save results summary
    results_summary_path = output_dir / f"{example_name}_notebook_results.md"
    with open(results_summary_path, 'w') as f:
        f.write(f"# {example_name} Results\n\n")
        f.write(f"- **Status**: {'VALID' if validation_report.is_valid else 'INVALID'}\n")
        f.write(f"- **Gears**: {len(gears)}\n")
        f.write(f"- **Total Volume**: {total_volume:.2f}\n")
        f.write(f"- **Torque Error**: {torque_error:.1f}%\n")
        f.write(f"- **Timestamp**: {pd.Timestamp.now()}\n")
    
    print(f"\n✅ Results summary saved to: {results_summary_path}")
    
    print("\n🎉 GearRL pipeline execution completed successfully!")

if __name__ == "__main__":
    main()
