#!/usr/bin/env python3
"""
Demo script for experimental data visualization.
Shows how to use the ExperimentalDataVisualizer class.
"""

import sys
import os
import json
sys.path.append('/home/mingwucn/Work/GearRL')

from kilo.skills.experimental_visualization_skills import ExperimentalDataVisualizer

def main():
    """Demo the experimental visualization capabilities."""
    
    # Initialize visualizer
    visualizer = ExperimentalDataVisualizer("data/exp")
    
    print(f"Available experiments: {visualizer.available_experiments}")
    
    if not visualizer.available_experiments:
        print("No experimental data found. Creating demo structure...")
        
        # Create demo experimental data structure
        demo_exp_dir = "data/exp/demo_experiment"
        os.makedirs(demo_exp_dir, exist_ok=True)
        os.makedirs(f"{demo_exp_dir}/layouts", exist_ok=True)
        
        # Create demo metrics
        import pandas as pd
        demo_metrics = pd.DataFrame({
            'step': range(100),
            'reward': [i * 0.1 for i in range(100)],
            'success_rate': [0.1 + i * 0.01 for i in range(100)],
            'constraint_violations': [10 - i * 0.1 for i in range(100)]
        })
        demo_metrics.to_csv(f"{demo_exp_dir}/metrics.csv", index=False)
        
        # Create demo results
        demo_results = {
            "final_reward": 9.9,
            "success_rate": 1.0,
            "avg_constraint_violations": 0.0,
            "total_episodes": 1000
        }
        with open(f"{demo_exp_dir}/results.json", "w") as f:
            json.dump(demo_results, f, indent=2)
        
        # Create demo constraints  
        demo_constraints = {
            "torque_ratio": "1:2",
            "min_gear_size": 15,
            "max_gear_size": 50,
            "boundary_margin": 10.0
        }
        with open(f"{demo_exp_dir}/constraints.json", "w") as f:
            json.dump(demo_constraints, f, indent=2)
        
        # Create demo layouts
        demo_layout = [
            {"id": "gear_0", "center": {"x": 0, "y": 0}, "teeth_count": [20], "module": 1.0},
            {"id": "gear_1", "center": {"x": 20, "y": 0}, "teeth_count": [15], "module": 1.0}
        ]
        with open(f"{demo_exp_dir}/layouts/layout_001.json", "w") as f:
            json.dump(demo_layout, f, indent=2)
        
        print(f"Created demo experiment at {demo_exp_dir}")
        
        # Reinitialize visualizer
        visualizer = ExperimentalDataVisualizer("data/exp")
        print(f"Available experiments after demo creation: {visualizer.available_experiments}")
    
    # Demonstrate visualization capabilities
    if visualizer.available_experiments:
        exp_name = visualizer.available_experiments[0]
        
        print(f"\nDemonstrating visualization for {exp_name}...")
        
        # Plot training metrics
        try:
            visualizer.plot_training_metrics(exp_name, f"demo_{exp_name}_metrics.png")
        except Exception as e:
            print(f"Metrics plot failed: {e}")
        
        # Generate text report
        try:
            report = visualizer.generate_experiment_report(exp_name)
            with open(f"demo_{exp_name}_report.md", "w") as f:
                f.write(report)
            print(f"Report saved to demo_{exp_name}_report.md")
        except Exception as e:
            print(f"Report generation failed: {e}")

if __name__ == "__main__":
    main()
