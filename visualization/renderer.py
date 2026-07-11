import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
from typing import List, Tuple, Dict, Any
from common.data_models import SystemDefinition, Boundary, Point, Constraints, Gear
import numpy as np
import json
import os

class Renderer:
    @staticmethod
    def render_system(system: SystemDefinition, output_path: str,
                      path: List[Tuple[float, float]] = None, 
                      gears: List[Gear] = None) -> None:
        """
        Render a gear system, including outlines of generated gears and their IDs.
        """
        if len(system.boundary.points) < 3:
            raise ValueError("Rendering requires a boundary with at least three points")
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Plot boundary polygon
        boundary_points = [(p.x, p.y) for p in system.boundary.points]
        boundary_poly = Polygon(boundary_points, closed=True, fill=False, color='black', linewidth=2)
        ax.add_patch(boundary_poly)
        
        # Plot generated gears if provided
        if gears:
            for gear in gears:
                # For compound gears, find the largest radius for annotation positioning
                radii = [d / 2 for d in gear.diameters]
                largest_radius = max(radii)
                
                # Draw a circle outline for each gear in the set
                for radius in radii:
                    gear_circle = Circle(
                        (gear.center.x, gear.center.y), radius,
                        fill=False, # Draw as an outline
                        edgecolor='darkblue', linewidth=1.5
                    )
                    ax.add_patch(gear_circle)
                
                # Add a dot for the center of the gear set
                ax.plot(gear.center.x, gear.center.y, 'ko', markersize=3)


        # Plot input and output shafts
        ax.plot(system.input_shaft.x, system.input_shaft.y, 'ro', markersize=10)
        ax.plot(system.output_shaft.x, system.output_shaft.y, 'bo', markersize=10)
        
        # Plot path if provided
        if path:
            # print(path)
            path_x = [p.x for p in path]
            path_y = [p.y for p in path]
            ax.plot(path_x, path_y, 'm-', linewidth=1, alpha=0.7)
        
        # Set plot properties
        all_x = [p[0] for p in boundary_points]
        all_y = [p[1] for p in boundary_points]
        ax.set_xlim(min(all_x) - 10, max(all_x) + 10)
        ax.set_ylim(min(all_y) - 10, max(all_y) + 10)
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.grid(True)
        ax.set_xticks([])
        ax.set_yticks([])
        
        fig.savefig(output_path, bbox_inches='tight', dpi=150)
        plt.close(fig)

    @staticmethod
    def render_processed_data(processed_data_path: str, output_path: str, 
                              path: List[Tuple[float, float]] = None, 
                              gears: List[Gear] = None) -> None:
        """
        Render processed data from JSON, optionally including a path and generated gears.
        """
        with open(processed_data_path, 'r') as f:
            data = json.load(f)
            
        norm_space = data['normalized_space']
        
        # Create a minimal SystemDefinition from the processed data
        system = SystemDefinition(
            boundary=Boundary(points=[Point(x=p[0], y=p[1]) for p in norm_space['boundaries']]),
            input_shaft=Point(x=norm_space['input_shaft']['x'], y=norm_space['input_shaft']['y']),
            output_shaft=Point(x=norm_space['output_shaft']['x'], y=norm_space['output_shaft']['y']),
            constraints=None # Constraints are not needed for rendering
        )
        
        # Render the system with optional path and gears
        Renderer.render_system(system, output_path, path, gears)

    @staticmethod
    def render_path(processed_data_path: str, output_path: str, path: List[Tuple[float, float]]):
        """
        Renders only the normalized boundaries, shafts, and a given path.
        """
        with open(processed_data_path, 'r') as f:
            data = json.load(f)['normalized_space']

        boundary_points = data['boundaries']
        input_shaft = tuple(data['input_shaft'].values())
        output_shaft = tuple(data['output_shaft'].values())

        fig, ax = plt.subplots(figsize=(12, 12))

        # Plot boundary polygon
        boundary_poly = Polygon(boundary_points, closed=True, fill=False, color='black', linewidth=2)
        ax.add_patch(boundary_poly)

        # Plot input and output shafts
        ax.plot(input_shaft[0], input_shaft[1], 'ro', markersize=10)
        ax.plot(output_shaft[0], output_shaft[1], 'bo', markersize=10)

        # print(path)
        # Plot path
        path_x = [p[0] for p in path]
        path_y = [p[1] for p in path]
        ax.plot(path_x, path_y, 'm-', linewidth=2)

        # Set plot properties
        all_x = [p[0] for p in boundary_points]
        all_y = [p[1] for p in boundary_points]
        ax.set_xlim(min(all_x) - 10, max(all_x) + 10)
        ax.set_ylim(min(all_y) - 10, max(all_y) + 10)
        # ax.set_xlim(-60,60)
        # ax.set_ylim(-60,60)
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.grid(True)
        ax.set_xticks([])
        ax.set_yticks([])

        fig.savefig(output_path, bbox_inches='tight', dpi=150)
        plt.close(fig)

if __name__ == "__main__":
    fn = 'Example1'
    
    CONFIG = {
        "INPUT_DIR": "../data",
        "INTERMEDIATE_DIR": "../data/intermediate",
        "EXAMPLE_NAME": f"{fn}",
        "module": 1.0,
        "clearance_margin": 1.0,
        "initial_gear_teeth": 20,
        "OUTPUT_DIR": "../output",
    }
    processed_json_path = os.path.join(CONFIG["INTERMEDIATE_DIR"], f"{CONFIG['EXAMPLE_NAME']}_processed.json")
    path_json_path = os.path.join(CONFIG['OUTPUT_DIR'], 'path.json')
    path_image_path = os.path.join(CONFIG['OUTPUT_DIR'], 'path.png')
    output_dir = os.path.join(CONFIG["OUTPUT_DIR"], CONFIG["EXAMPLE_NAME"])
    output_image_path = os.path.join(output_dir, "gear_train_result.png")
    gear_layout_path = os.path.join(output_dir, "gear_layout.json")

    with open(gear_layout_path, 'r') as f:
        gears_data = json.load(f)

    gears_for_renderer = [Gear.from_json(g) for g in gears_data]

    Renderer.render_processed_data(
        processed_data_path=processed_json_path,
        output_path=output_image_path,
        gears=gears_for_renderer
    )
