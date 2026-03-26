import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
import sys
import os
sys.path.append('../')

from geometry_env.simulator import GearTrainSimulator
from gear_generator.factory import GearFactory
from pathfinding.finder import Pathfinder
from common.data_models import Gear, Point, SystemDefinition, Boundary, Constraints, GearLayout
from physics_validator.fixed_validator import FixedPhysicsValidator

class FixedGearEnv(gym.Env):
    """
    A Gymnasium environment for the gear train generation problem with proper constraint enforcement.
    The agent learns to place simple and compound gears to connect two shafts while respecting all constraints.
    """
    metadata = {"render_modes": [], "render_fps": 4}

    def __init__(self, config: dict):
        """
        Initializes the environment with integrated physics validation.
        Args:
            config (dict): Configuration with properly aligned constraints.
        """
        super().__init__()
        self.config = config
        
        # --- Load system definition for validation ---
        processed_json_path = config["json_path"]
        with open(processed_json_path, 'r') as f:
            data = json.load(f)['normalized_space']
        
        # Load corresponding constraint file
        constraint_file = processed_json_path.replace('intermediate/', '').replace('_processed.json', '_constraints.json')
        if not os.path.exists(constraint_file):
            # Try alternative path
            constraint_file = constraint_file.replace('data/', '')
            constraint_file = f"data/{constraint_file}"
        
        with open(constraint_file, 'r') as f:
            constraint_data = json.load(f)
        
        self.system_definition = SystemDefinition(
            boundary=Boundary(points=[Point(p[0], p[1]) for p in data['boundaries']]),
            input_shaft=Point(data['input_shaft']['x'], data['input_shaft']['y']),
            output_shaft=Point(data['output_shaft']['x'], data['output_shaft']['y']),
            constraints=Constraints.from_json(constraint_data)
        )
        
        # --- Run Pathfinding ---
        pathfinder = Pathfinder()
        self.optimal_path = pathfinder.find_path(processed_json_path)
        if not self.optimal_path:
            raise RuntimeError(f"Pathfinder failed to find a path for {processed_json_path}")
            
        # --- Define Action and Observation Spaces (aligned with constraints) ---
        self.min_teeth = constraint_data.get("min_gear_size", config.get("min_gear_teeth", 8))
        self.max_teeth = constraint_data.get("max_gear_size", config.get("max_gear_teeth", 40))
        num_choices = self.max_teeth - self.min_teeth + 1

        # Action Space: [driven_teeth, driving_teeth] for compound gears
        self.action_space = spaces.MultiDiscrete([num_choices, num_choices])
        
        # Observation Space includes constraint info
        low_bounds = np.array([-500, -500, self.min_teeth, 0, 0], dtype=np.float32)
        high_bounds = np.array([500, 500, self.max_teeth, 500, 1000], dtype=np.float32)
        self.observation_space = spaces.Box(low=low_bounds, high=high_bounds, dtype=np.float32)

        # --- Initialize Simulation Engine ---
        gear_factory = GearFactory(module=config.get("module", 1.0))
        
        self.simulator = GearTrainSimulator(
            path=self.optimal_path,
            input_shaft=tuple(data['input_shaft'].values()),
            output_shaft=tuple(data['output_shaft'].values()),
            boundaries=data['boundaries'],
            gear_factory=gear_factory,
            clearance_margin=config.get("clearance_margin", 1.0)
        )
        
        # Initialize physics validator
        self.validator = FixedPhysicsValidator()

    def _state_to_observation(self, state: dict) -> np.ndarray:
        """Convert simulator state to observation array."""
        if state is None:
            return np.zeros(self.observation_space.shape, dtype=np.float32)
            
        return np.array([
            state["last_gear_center_x"],
            state["last_gear_center_y"], 
            state["last_gear_teeth"],
            state["last_gear_radius"],
            state["distance_to_target"]
        ], dtype=np.float32)

    def reset(self, seed=None, options=None):
        """Reset environment ensuring valid initial state."""
        super().reset(seed=seed)
        
        initial_teeth = self.config.get("initial_gear_teeth", 20)
        # Ensure initial teeth respects constraints
        initial_teeth = max(self.min_teeth, min(self.max_teeth, initial_teeth))
        
        state, _, _, info = self.simulator.reset(initial_gear_teeth=initial_teeth)
        observation = self._state_to_observation(state)
        return observation, info

    def step(self, action: np.ndarray):
        """Execute step with integrated physics validation."""
        # Map action to tooth counts respecting constraints
        driven_teeth = self.min_teeth + action[0]
        driving_teeth = self.min_teeth + action[1]
        
        # Validate action against constraints before execution
        if driven_teeth < self.min_teeth or driven_teeth > self.max_teeth:
            return self._get_invalid_action_response()
        if driving_teeth < self.min_teeth or driving_teeth > self.max_teeth:
            return self._get_invalid_action_response()
            
        action_tuple = (driven_teeth, driving_teeth)
        
        # Execute action in simulator
        state, reward, done, info = self.simulator.step(action_tuple)
        
        # Perform comprehensive physics validation on current layout
        if not done:  # Only validate if simulation didn't terminate
            validation_reward, validation_done, validation_info = self._validate_current_layout()
            if validation_done:
                # Override simulator results with validation results
                reward = validation_reward
                done = True
                info.update(validation_info)
        
        observation = self._state_to_observation(state)
        terminated = done
        truncated = False

        return observation, reward, terminated, truncated, info
    
    def _validate_current_layout(self):
        """Perform physics validation on current gear layout."""
        try:
            # Create GearLayout from simulator state
            gear_layout = GearLayout(gears=[
                Gear(
                    id=g.id,
                    center=Point(g.center.x, g.center.y),
                    teeth_count=g.teeth_count,
                    module=1.0  # Assuming module=1.0 as per examples
                ) for g in self.simulator.gears
            ])
            
            # Validate layout
            report = self.validator.check_layout(gear_layout, self.system_definition)
            
            if not report.is_valid:
                # Constraint violation - penalize heavily
                error_msg = "; ".join(report.errors[:3])  # First 3 errors
                return -100.0, True, {"error": f"Constraint violation: {error_msg}"}
            
            # Check if successfully connected to output
            if len(self.simulator.gears) >= 2:
                last_gear = self.simulator.gears[-2]  # Second to last (last is output)
                output_gear = self.simulator.gears[-1]
                
                dist_to_output = np.sqrt(
                    (last_gear.center.x - output_gear.center.x)**2 +
                    (last_gear.center.y - output_gear.center.y)**2
                )
                required_dist = last_gear.driving_radius + output_gear.driven_radius
                
                if abs(dist_to_output - required_dist) < 0.5:
                    # Success! Validate torque ratio specifically
                    torque_error = self._check_torque_ratio_specific(gear_layout)
                    if torque_error == "":
                        return 100.0, True, {"success": "Valid gear train with correct torque ratio"}
                    else:
                        return -50.0, True, {"error": f"Torque ratio mismatch: {torque_error}"}
            
            # Valid intermediate state
            return -1.0, False, {}
            
        except Exception as e:
            return -100.0, True, {"error": f"Validation error: {str(e)}"}
    
    def _check_torque_ratio_specific(self, layout):
        """Check torque ratio with proper error handling."""
        target_ratio_str = self.system_definition.constraints.torque_ratio
        if target_ratio_str == "free":
            return ""
            
        try:
            ratio_parts = target_ratio_str.split(":")
            if len(ratio_parts) != 2:
                return f"Invalid torque ratio format: {target_ratio_str}"
            
            target_value = float(ratio_parts[0]) / float(ratio_parts[1])
            
            # Find input and output gears
            input_gear = min(layout.gears, key=lambda g: 
                np.sqrt((g.center.x - self.system_definition.input_shaft.x)**2 + 
                       (g.center.y - self.system_definition.input_shaft.y)**2))
            output_gear = min(layout.gears, key=lambda g: 
                np.sqrt((g.center.x - self.system_definition.output_shaft.x)**2 + 
                       (g.center.y - self.system_definition.output_shaft.y)**2))
            
            actual_ratio = input_gear.teeth_count[0] / output_gear.teeth_count[0]
            
            if not np.isclose(actual_ratio, target_value, rtol=0.05):
                return f"actual {actual_ratio:.2f} != target {target_value:.2f}"
            
            return ""
            
        except Exception as e:
            return f"torque validation error: {str(e)}"
    
    def _get_invalid_action_response(self):
        """Return response for invalid actions."""
        dummy_state = {
            "last_gear_center_x": 0,
            "last_gear_center_y": 0, 
            "last_gear_teeth": self.min_teeth,
            "last_gear_radius": 0,
            "distance_to_target": 100
        }
        observation = self._state_to_observation(dummy_state)
        return observation, -100.0, True, {"error": "Invalid action: gear size outside constraints"}, {}

    def close(self):
        """Cleanup."""
        pass
