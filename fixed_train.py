#!/usr/bin/env python3
"""
Fixed training script for GearRL with proper constraint enforcement.
"""

import time
import os
import json
import argparse
import numpy as np
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from geometry_env.fixed_env import FixedGearEnv
from rl_agent.agents.ppo_agent import PPOAgent 

def main():
    parser = argparse.ArgumentParser(description='Train RL agent for gear train generation with constraint enforcement')
    parser.add_argument('--config_path', type=str, required=True, help='Path to the environment config JSON file.')
    parser.add_argument('--episodes', type=int, default=10000, help='Number of training episodes')
    parser.add_argument('--max_steps_per_episode', type=int, default=10, help='Maximum steps per episode')
    parser.add_argument('--update_timestep', type=int, default=2048, help='Number of steps to collect before updating the policy')
    parser.add_argument('--learning_rate', type=float, default=3e-4, help='Learning rate for optimizer')
    parser.add_argument('--gamma', type=float, default=0.99, help='Discount factor')
    parser.add_argument('--clip_epsilon', type=float, default=0.2, help='PPO clip parameter')
    parser.add_argument('--log_interval', type=int, default=1, help='Log progress every N episodes')
    parser.add_argument('--output_dir', type=str, default='models', help='Directory to save models')
    
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # --- Environment and Agent Setup ---
    with open(args.config_path, 'r') as f:
        env_config = json.load(f)
    env = FixedGearEnv(env_config)

    state_dim = env.observation_space.shape[0]
    action_dims = env.action_space.nvec
    agent = PPOAgent(state_dim=state_dim, action_dims=action_dims, lr=args.learning_rate, gamma=args.gamma, clip_epsilon=args.clip_epsilon)

    print("--- Starting Agent Training with Constraint Enforcement ---")
    start_time = time.time()
    
    time_step_counter = 0
    
    # --- Training Loop ---
    for episode in range(1, args.episodes + 1):
        state, _ = env.reset()
        episode_reward = 0
        
        for step in range(args.max_steps_per_episode):
            time_step_counter += 1
            
            action, log_prob = agent.act(state)
            next_state, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            agent.memory.add(state, action, reward, done, log_prob)

            # Update the policy only when enough data is collected
            if time_step_counter % args.update_timestep == 0:
                loss = agent.update()
                print(f"Episode {episode} | Timestep {time_step_counter} | Policy Updated | Loss: {loss:.4f}")

            state = next_state
            episode_reward += reward
            if done:
                break
        
        if episode % args.log_interval == 0:
            success_msg = "SUCCESS" if any("success" in str(v) for v in info.values()) else "FAILED"
            print(f"Episode {episode} | Episode Reward: {episode_reward:.2f} | Status: {success_msg}")

    end_time = time.time()
    print(f"--- Training Finished in {end_time - start_time:.2f}s ---")
    
    model_path = os.path.join(args.output_dir, "ppo_gear_placer_fixed.pt")
    agent.save(model_path)
    
    env.close()

if __name__ == "__main__":
    main()
