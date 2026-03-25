#!/usr/bin/env python3
"""
Demo script for experimental data visualization in GearRL.
"""

import sys
import os
sys.path.append('.')
sys.path.append('.kilo')

from skills.experimental_visualization_skills import ExperimentalDataVisualizer

def main():
    """Run demonstration of experimental visualization capabilities."""
    
    print("GearRL Experimental Data Visualization Demo")
    print("=" * 50)
    
    # Initialize visualizer with experimental data directory
    visualizer = ExperimentalDataVisualizer('data/exp')
    
    print(f"Available experiments: {visualizer.available_experiments}")
    
    if not visualizer.available_experiments:
        print("No experimental data found!")
        return
    
    # Use the first available experiment
    exp_name = visualizer.available_experiments[0]
    print(f"\nDemonstrating visualization for: {exp_name}")
    
    try:
        # 1. Generate text report
        print("\n1. Generating text report...")
        report = visualizer.generate_experiment_report(exp_name)
        report_file = f"{exp_name}_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"   Report saved to: {report_file}")
        
        # 2. Plot training metrics
        print("\n2. Creating training metrics plot...")
        metrics_plot = f"{exp_name}_metrics.png"
        visualizer.plot_training_metrics(exp_name, metrics_plot)
        print(f"   Metrics plot saved to: {metrics_plot}")
        
        # 3. Create layout evolution visualization (if multiple layouts exist)
        print("\n3. Creating layout evolution visualization...")
        layout_plot = f"{exp_name}_layouts.png"
        visualizer.visualize_layout_evolution(exp_name, num_layouts=2, save_path=layout_plot)
        print(f"   Layout evolution plot saved to: {layout_plot}")
        
        # 4. Compare experiments (if multiple exist)
        if len(visualizer.available_experiments) > 1:
            print("\n4. Creating experiment comparison...")
            comp_plot = "experiment_comparison.png"
            visualizer.plot_experiment_comparison(
                visualizer.available_experiments, 
                metric="success_rate",
                save_path=comp_plot
            )
            print(f"   Comparison plot saved to: {comp_plot}")
        
        print(f"\n✅ Demo completed successfully!")
        print(f"   Generated files:")
        print(f"   - {report_file}")
        print(f"   - {metrics_plot}")  
        print(f"   - {layout_plot}")
        if len(visualizer.available_experiments) > 1:
            print(f"   - {comp_plot}")
            
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
