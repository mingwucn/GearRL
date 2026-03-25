"""
Experimental data visualization skills for GearRL system.
Handles visualization of experimental results, training logs, and performance metrics.
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import glob


class ExperimentalDataVisualizer:
    """Visualizes experimental data from GearRL experiments."""
    
    def __init__(self, exp_data_dir: str = "data/exp"):
        """Initialize with experimental data directory path."""
        self.exp_data_dir = Path(exp_data_dir)
        self.available_experiments = []
        if self.exp_data_dir.exists():
            self.available_experiments = [d.name for d in self.exp_data_dir.iterdir() 
                                        if d.is_dir()]
    
    def load_experiment_data(self, experiment_name: str) -> Dict[str, Any]:
        """
        Load experimental data for a specific experiment.
        
        Expected file structure:
        data/exp/{experiment_name}/
        ├── metrics.csv              # Training metrics
        ├── results.json             # Final results  
        ├── constraints.json         # Experiment constraints
        └── layouts/                 # Generated layouts
            ├── layout_001.json
            ├── layout_002.json
            └── ...
        """
        exp_path = self.exp_data_dir / experiment_name
        if not exp_path.exists():
            raise FileNotFoundError(f"Experiment {experiment_name} not found in {self.exp_data_dir}")
        
        data = {}
        
        # Load metrics CSV if exists
        metrics_file = exp_path / "metrics.csv"
        if metrics_file.exists():
            data['metrics'] = pd.read_csv(metrics_file)
        
        # Load results JSON if exists  
        results_file = exp_path / "results.json"
        if results_file.exists():
            with open(results_file, 'r') as f:
                data['results'] = json.load(f)
        
        # Load constraints if exists
        constraints_file = exp_path / "constraints.json" 
        if constraints_file.exists():
            with open(constraints_file, 'r') as f:
                data['constraints'] = json.load(f)
        
        # Load layouts if directory exists
        layouts_dir = exp_path / "layouts"
        if layouts_dir.exists():
            layout_files = sorted(glob.glob(str(layouts_dir / "*.json")))
            data['layouts'] = []
            for layout_file in layout_files[:10]:  # Limit to first 10 for performance
                with open(layout_file, 'r') as f:
                    layout_data = json.load(f)
                    data['layouts'].append(layout_data)
        
        return data
    
    def plot_training_metrics(self, experiment_name: str, save_path: Optional[str] = None):
        """Plot training metrics for an experiment."""
        try:
            data = self.load_experiment_data(experiment_name)
            if 'metrics' not in data:
                print(f"No metrics data found for {experiment_name}")
                return
            
            metrics = data['metrics']
            
            # Identify metric columns (exclude step/epoch columns)
            metric_cols = [col for col in metrics.columns 
                          if col not in ['step', 'epoch', 'iteration']]
            
            if not metric_cols:
                print(f"No metric columns found in {experiment_name}")
                return
            
            # Create subplots
            n_metrics = len(metric_cols)
            cols = min(3, n_metrics)
            rows = (n_metrics + cols - 1) // cols
            
            fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))
            if n_metrics == 1:
                axes = [axes]
            elif rows == 1:
                axes = axes if cols > 1 else [axes]
            else:
                axes = axes.flatten()
            
            # Plot each metric
            for i, metric_col in enumerate(metric_cols):
                if i < len(axes):
                    x_col = 'step' if 'step' in metrics.columns else (
                           'epoch' if 'epoch' in metrics.columns else 
                           range(len(metrics)))
                    
                    axes[i].plot(x_col if isinstance(x_col, range) else metrics[x_col], 
                               metrics[metric_col])
                    axes[i].set_title(f'{metric_col.replace("_", " ").title()}')
                    axes[i].set_xlabel('Step' if 'step' in metrics.columns else 
                                     'Epoch' if 'epoch' in metrics.columns else 'Iteration')
                    axes[i].grid(True, alpha=0.3)
            
            # Hide unused subplots
            for i in range(n_metrics, len(axes)):
                axes[i].set_visible(False)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"Training metrics plot saved to {save_path}")
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error plotting training metrics for {experiment_name}: {e}")
    
    def plot_experiment_comparison(self, experiment_names: List[str], 
                                 metric: str = "success_rate", 
                                 save_path: Optional[str] = None):
        """Compare a specific metric across multiple experiments."""
        if not self.available_experiments:
            print("No experimental data available")
            return
        
        # Filter valid experiment names
        valid_exps = [exp for exp in experiment_names if exp in self.available_experiments]
        if not valid_exps:
            print(f"None of the specified experiments found: {experiment_names}")
            return
        
        values = []
        labels = []
        
        for exp_name in valid_exps:
            try:
                data = self.load_experiment_data(exp_name)
                if 'results' in data and metric in data['results']:
                    values.append(data['results'][metric])
                    labels.append(exp_name)
                elif 'metrics' in data and metric in data['metrics'].columns:
                    # Use final value from metrics
                    values.append(data['metrics'][metric].iloc[-1])
                    labels.append(exp_name)
            except Exception as e:
                print(f"Skipping {exp_name} due to error: {e}")
        
        if not values:
            print(f"No data found for metric '{metric}' in specified experiments")
            return
        
        # Create comparison bar plot
        plt.figure(figsize=(10, 6))
        bars = plt.bar(range(len(values)), values)
        plt.xlabel('Experiments')
        plt.ylabel(metric.replace('_', ' ').title())
        plt.title(f'Comparison of {metric.replace("_", " ").title()} Across Experiments')
        plt.xticks(range(len(values)), labels, rotation=45, ha='right')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f'{value:.3f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Comparison plot saved to {save_path}")
        else:
            plt.show()
    
    def visualize_layout_evolution(self, experiment_name: str, 
                                  num_layouts: int = 5,
                                  save_path: Optional[str] = None):
        """Visualize evolution of generated layouts during training."""
        try:
            data = self.load_experiment_data(experiment_name)
            if 'layouts' not in data or len(data['layouts']) < 2:
                print(f"Insufficient layout data for {experiment_name}")
                return
            
            layouts = data['layouts'][:num_layouts]
            
            fig, axes = plt.subplots(1, len(layouts), figsize=(5*len(layouts), 5))
            if len(layouts) == 1:
                axes = [axes]
            
            for i, layout in enumerate(layouts):
                self._plot_single_layout(layout, axes[i], f"Layout {i+1}")
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"Layout evolution plot saved to {save_path}")
            else:
                plt.show()
                
        except Exception as e:
            print(f"Error visualizing layout evolution for {experiment_name}: {e}")
    
    def _plot_single_layout(self, layout: List[Dict], ax, title: str = ""):
        """Plot a single gear layout."""
        from common.data_models import GearLayout, Gear, Point
        
        try:
            # Convert to GearLayout object
            gear_layout = GearLayout.from_json(layout)
            
            # Plot gears as circles
            for i, gear in enumerate(gear_layout.gears):
                from matplotlib.patches import Circle
                circle = Circle((gear.center.x, gear.center.y), 
                              gear.diameters[0]/2, 
                              fill=False, linewidth=2)
                ax.add_patch(circle)
                ax.plot(gear.center.x, gear.center.y, 'r+', markersize=8)
                ax.annotate(f"G{i}", (gear.center.x, gear.center.y),
                          textcoords="offset points", xytext=(5,5), fontsize=8)
            
            ax.set_title(title)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            print(f"Error plotting layout: {e}")
            # Fallback: plot raw coordinates if model conversion fails
            for i, gear_data in enumerate(layout):
                center = gear_data['center']
                diameter = gear_data['teeth_count'][0]  # Approximate diameter
                from matplotlib.patches import Circle
                circle = Circle((center['x'], center['y']), diameter/2, 
                              fill=False, linewidth=2)
                ax.add_patch(circle)
                ax.plot(center['x'], center['y'], 'r+', markersize=8)
            ax.set_title(title)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
    
    def generate_experiment_report(self, experiment_name: str) -> str:
        """Generate a text report for an experiment."""
        try:
            data = self.load_experiment_data(experiment_name)
            report = f"# Experiment Report: {experiment_name}\n\n"
            
            if 'results' in data:
                report += "## Results Summary\n\n"
                for key, value in data['results'].items():
                    report += f"- **{key.replace('_', ' ').title()}**: {value}\n"
                report += "\n"
            
            if 'metrics' in data:
                report += "## Metrics Summary\n\n"
                metrics = data['metrics']
                for col in metrics.columns:
                    if col not in ['step', 'epoch']:
                        final_val = metrics[col].iloc[-1]
                        report += f"- **{col.replace('_', ' ').title()}**: {final_val:.4f}\n"
                report += "\n"
            
            if 'layouts' in data:
                report += f"## Layouts Generated\n\n"
                report += f"- **Total layouts**: {len(data['layouts'])}\n"
                # Analyze first layout
                if data['layouts']:
                    first_layout = data['layouts'][0]
                    total_gears = len(first_layout)
                    teeth_counts = []
                    for gear in first_layout:
                        teeth_counts.extend(gear['teeth_count'])
                    avg_teeth = sum(teeth_counts) / len(teeth_counts) if teeth_counts else 0
                    report += f"- **Gears in first layout**: {total_gears}\n"
                    report += f"- **Average teeth**: {avg_teeth:.2f}\n"
            
            if 'constraints' in data:
                report += "\n## Constraints\n\n"
                for key, value in data['constraints'].items():
                    report += f"- **{key.replace('_', ' ').title()}**: {value}\n"
            
            return report
            
        except Exception as e:
            return f"# Error generating report for {experiment_name}\n\n{str(e)}"


# Utility functions for common visualization tasks
def quick_plot_metrics(file_path: str, save_path: Optional[str] = None):
    """Quick utility to plot metrics from a CSV file."""
    try:
        df = pd.read_csv(file_path)
        metric_cols = [col for col in df.columns if col not in ['step', 'epoch', 'iteration']]
        
        if not metric_cols:
            print("No metric columns found")
            return
        
        plt.figure(figsize=(12, 8))
        for i, col in enumerate(metric_cols):
            plt.subplot(len(metric_cols), 1, i+1)
            x_col = 'step' if 'step' in df.columns else (
                   'epoch' if 'epoch' in df.columns else range(len(df)))
            plt.plot(x_col if isinstance(x_col, range) else df[x_col], df[col])
            plt.title(col.replace('_', ' ').title())
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
            
    except Exception as e:
        print(f"Error in quick_plot_metrics: {e}")


def compare_multiple_experiments(exp_dirs: List[str], metric: str = "reward"):
    """Compare multiple experiment directories directly."""
    visualizer = ExperimentalDataVisualizer()
    
    # Try to extract experiment names from paths
    exp_names = []
    for exp_dir in exp_dirs:
        exp_name = Path(exp_dir).name
        if (Path("data/exp") / exp_name).exists():
            exp_names.append(exp_name)
    
    if exp_names:
        visualizer.plot_experiment_comparison(exp_names, metric)
    else:
        print("No matching experiments found in data/exp directory")
