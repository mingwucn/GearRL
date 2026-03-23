"""
Visualization skills for GearRL system handling matplotlib rendering.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from common.data_models import SystemDefinition, Boundary, Point, Gear


class VisualizationSkill:
    """Handles visualization of gear systems and components."""
    
    def __init__(self, figsize: Tuple[float, float] = (12, 12), dpi: int = 300):
        self.figsize = figsize
        self.dpi = dpi
    
    def render_system(self, system: SystemDefinition, output_path: str, 
                     path: Optional[List[Point]] = None, 
                     gears: Optional[List[Gear]] = None) -> None:
        """
        Render a complete gear system visualization.
        
        Args:
            system: System definition with boundary and shafts
            output_path: Path to save the rendered image
            path: Optional path points to display
            gears: Optional list of gears to render
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Plot boundary polygon
        boundary_points = [(p.x, p.y) for p in system.boundary.points]
        boundary_poly = Polygon(boundary_points, closed=True, fill=False, color='black', linewidth=2)
        ax.add_patch(boundary_poly)
        
        # Plot generated gears if provided
        if gears:
            for gear in gears:
                # For compound gears, find the largest radius for annotation positioning
                radii = [d / 2.0 for d in gear.diameters]
                largest_radius = max(radii)
                
                # Draw a circle outline for each gear in the set
                for radius in radii:
                    gear_circle = Circle(
                        (gear.center.x, gear.center.y), radius,
                        fill=False,  # Draw as an outline
                        edgecolor='darkblue', linewidth=1.5
                    )
                    ax.add_patch(gear_circle)
                
                # Add a dot for the center of the gear set
                ax.plot(gear.center.x, gear.center.y, 'ko', markersize=3)

                # Add the gear ID text annotation on the edge of the largest circle
                angle_rad = np.deg2rad(45)
                text_x = gear.center.x + (largest_radius + 1.0) * np.cos(angle_rad)
                text_y = gear.center.y - (largest_radius + 1.0) * np.sin(angle_rad)
                ax.text(text_x, text_y, gear.id, fontsize=9, ha='center', va='center', color='darkgreen')

        # Plot input and output shafts
        ax.plot(system.input_shaft.x, system.input_shaft.y, 'ro', markersize=10, label='Input Shaft')
        ax.plot(system.output_shaft.x, system.output_shaft.y, 'bo', markersize=10, label='Output Shaft')
        
        # Plot path if provided
        if path:
            path_x = [p.x for p in path]
            path_y = [p.y for p in path]
            ax.plot(path_x, path_y, 'm-', linewidth=1, alpha=0.7, label='Path')
        
        # Set plot properties
        all_x = [p[0] for p in boundary_points]
        all_y = [p[1] for p in boundary_points]
        ax.set_xlim(min(all_x) - 10, max(all_x) + 10)
        ax.set_ylim(min(all_y) - 10, max(all_y) + 10)
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.grid(True)
        ax.legend()
        ax.set_title('Gear System Visualization')
        
        plt.savefig(output_path, bbox_inches='tight', dpi=self.dpi)
        plt.close()
    
    def render_path_only(self, boundaries: List[Point], start: Point, goal: Point, 
                        path: List[Point], output_path: str) -> None:
        """
        Render only the path and boundary without gears.
        
        Args:
            boundaries: Boundary polygon points
            start: Starting point (input shaft)
            goal: Goal point (output shaft)
            path: Path points to render
            output_path: Path to save the rendered image
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Plot boundary polygon
        boundary_points = [(p.x, p.y) for p in boundaries]
        boundary_poly = Polygon(boundary_points, closed=True, fill=False, color='black', linewidth=2)
        ax.add_patch(boundary_poly)
        
        # Plot start and goal points
        ax.plot(start.x, start.y, 'ro', markersize=10, label='Input Shaft')
        ax.plot(goal.x, goal.y, 'bo', markersize=10, label='Output Shaft')
        
        # Plot path
        path_x = [p.x for p in path]
        path_y = [p.y for p in path]
        ax.plot(path_x, path_y, 'm-', linewidth=2, label='Path')
        
        # Set plot properties
        all_x = [p[0] for p in boundary_points]
        all_y = [p[1] for p in boundary_points]
        ax.set_xlim(min(all_x) - 10, max(all_x) + 10)
        ax.set_ylim(min(all_y) - 10, max(all_y) + 10)
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.grid(True)
        ax.legend()
        ax.set_title('Path Visualization')
        
        plt.savefig(output_path, bbox_inches='tight', dpi=self.dpi)
        plt.close()
    
    def render_gear_layout_comparison(self, system: SystemDefinition, 
                                    layouts: List[List[Gear]], 
                                    output_path: str) -> None:
        """
        Render multiple gear layouts for comparison.
        
        Args:
            system: System definition
            layouts: List of different gear layouts to compare
            output_path: Path to save the rendered image
        """
        n_layouts = len(layouts)
        if n_layouts == 0:
            return
            
        fig, axes = plt.subplots(1, n_layouts, figsize=(self.figsize[0] * n_layouts, self.figsize[1]))
        if n_layouts == 1:
            axes = [axes]
            
        for i, layout in enumerate(layouts):
            ax = axes[i]
            
            # Plot boundary
            boundary_points = [(p.x, p.y) for p in system.boundary.points]
            boundary_poly = Polygon(boundary_points, closed=True, fill=False, color='black', linewidth=2)
            ax.add_patch(boundary_poly)
            
            # Plot gears
            if layout:
                for gear in layout:
                    radii = [d / 2.0 for d in gear.diameters]
                    for radius in radii:
                        gear_circle = Circle(
                            (gear.center.x, gear.center.y), radius,
                            fill=False, edgecolor='darkblue', linewidth=1.5
                        )
                        ax.add_patch(gear_circle)
                    ax.plot(gear.center.x, gear.center.y, 'ko', markersize=3)
            
            # Plot shafts
            ax.plot(system.input_shaft.x, system.input_shaft.y, 'ro', markersize=10)
            ax.plot(system.output_shaft.x, system.output_shaft.y, 'bo', markersize=10)
            
            # Set properties
            all_x = [p[0] for p in boundary_points]
            all_y = [p[1] for p in boundary_points]
            ax.set_xlim(min(all_x) - 10, max(all_x) + 10)
            ax.set_ylim(min(all_y) - 10, max(all_y) + 10)
            ax.invert_yaxis()
            ax.set_aspect('equal')
            ax.grid(True)
            ax.set_title(f'Layout {i+1}')
            
        plt.savefig(output_path, bbox_inches='tight', dpi=self.dpi)
        plt.close()