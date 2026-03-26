#!/usr/bin/env python3
"""
Test FixedGearEnv step functionality.
"""

import sys
sys.path.append('.')

import json
from geometry_env.fixed_env import FixedGearEnv

def test_fixed_env_step():
    """Test FixedGearEnv step."""
    
    config = {'json_path': 'data/intermediate/Example1_processed.json'}
    env = FixedGearEnv(config)
    
    # Reset
    obs, info = env.reset()
    print(f"Reset observation shape: {obs.shape}")
    
    # Try a valid action
    action = [5, 10]  # driven_teeth offset, driving_teeth offset
    next_obs, reward, terminated, truncated, info = env.step(action)
    
    print(f"Step result: reward={reward}, terminated={terminated}, info={info}")
    
    env.close()

if __name__ == "__main__":
    test_fixed_env_step()