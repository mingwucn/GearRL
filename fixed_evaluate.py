#!/usr/bin/env python3
"""
Fixed evaluation script for GearRL with proper constraint validation.
"""

import os
import json
import argparse
import sys
import numpy as np

sys.path.append('.')

from geometry_env.fixed_env import FixedGearEnv
from rl_agent.agents.ppo_agent import PPOAgent
from visualization.renderer import Renderer
from common.data_models import GearLayout
from physics_validator.fixed_validator import FixedPhysicsValidator

def evaluate_agent():
    """
    Evaluates a trained PPO agent with comprehensive constraint validation.
    """
    parser = argparse.ArgumentParser(description='Evaluate trained RL agent with constraint validation.')
    parser.add_argument('--model_path', type=str, required=True, help='Path to the trained PPO model (.pt file).')
    parser.add_argument('--config_path', type=str, required=True, help='Path to the environment config JSON file.')
    parser.add_argument('--output_dir', type=str, default='output_eval_fixed', help='Directory to save evaluation results.')
    args = parser.parse_args()

    # --- Environment and Agent Setup ---
    print("--- Setting up Environment and Agent ---")
    with open(args.config_path, 'r') as f:
        env_config = json.load(f)

    env = FixedGearEnv(env_config)

    state_dim = env.observation_space.shape[0]
    action_dims = env.action_space.nvec

    agent = PPOAgent(state_dim, action_dims, lr=0, gamma=0, clip_epsilon=0)
    agent.load(args.model_path)

    # --- Run Evaluation Episode ---
    print("\n--- Running Evaluation Episode ---")
    state, _ = env.reset()
    done = False
    episode_reward = 0
    step_count = 0

    while not done:
        action, _ = agent.act(state)
        next_state, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
        state = next_state
        episode_reward += reward
        step_count += 1
        
        print(f"Step {step_count}: Action={action}, Reward={reward:.2f}")

    print(f"\n--- Episode Finished ---")
    if info.get("success"):
        print(f"Result: SUCCESS - {info['success']}")
    elif info.get("error"):
        print(f"Result: FAILED - {info['error']}")
    else:
        print("Result: Episode finished due to step limit.")
    print(f"Total Reward: {episode_reward:.2f}")

    # --- Comprehensive Validation ---
    example_name = os.path.basename(env_config['json_path']).replace('_processed.json', '')
    eval_output_dir = os.path.join(args.output_dir, f"{example_name}_eval")
    os.makedirs(eval_output_dir, exist_ok=True)
    
    # Save gear layout
    gear_layout_path = os.path.join(eval_output_dir, "evaluation_gear_layout.json")
    gears_json_data = [gear.to_json() for gear in env.simulator.gears]
    with open(gear_layout_path, 'w') as f:
        json.dump(gears_json_data, f, indent=4)
    print(f"\nGenerated gear layout saved to: {gear_layout_path}")

    # Perform final physics validation
    validator = FixedPhysicsValidator()
    gear_layout = GearLayout.from_json(gears_json_data)
    
    # Load system definition for validation
    processed_json_path = env_config['json_path']
    with open(processed_json_path, 'r') as f:
        data = json.load(f)['normalized_space']
    
    constraint_file = processed_json_path.replace('intermediate/', '').replace('_processed.json', '_constraints.json')
    if not os.path.exists(constraint_file):
        constraint_file = f"data/{os.path.basename(constraint_file)}"
    
    with open(constraint_file, 'r') as f:
        constraint_data = json.load(f)
    
    from common.data_models import SystemDefinition, Boundary, Point, Constraints
    system_definition = SystemDefinition(
        boundary=Boundary(points=[Point(p[0], p[1]) for p in data['boundaries']]),
        input_shaft=Point(data['input_shaft']['x'], data['input_shaft']['y']),
        output_shaft=Point(data['output_shaft']['x'], data['output_shaft']['y']),
        constraints=Constraints.from_json(constraint_data)
    )
    
    final_report = validator.check_layout(gear_layout, system_definition)
    
    validation_report_path = os.path.join(eval_output_dir, "validation_report.json")
    with open(validation_report_path, 'w') as f:
        json.dump(final_report.to_json(), f, indent=4)
    
    print(f"\nFinal validation report saved to: {validation_report_path}")
    print(f"Layout is valid: {final_report.is_valid}")
    if not final_report.is_valid:
        print("Validation errors:")
        for error in final_report.errors:
            print(f"  - {error}")
    
    # Render final result
    output_image_path = os.path.join(eval_output_dir, "evaluation_result.png")
    Renderer.render_processed_data(
        processed_data_path=env_config['json_path'],
        output_path=output_image_path,
        path=env.simulator.path,
        gear_layout_path=gear_layout_path
    )
    print(f"Final visualization saved to: {output_image_path}")
    
    env.close()

if __name__ == "__main__":
    evaluate_agent()
