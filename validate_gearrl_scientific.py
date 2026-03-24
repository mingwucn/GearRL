#!/usr/bin/env python3
"""
Scientific Validation Script for GearRL System
Identifies constraint violations and torque ratio failures.
"""

import json
import pandas as pd
from pathlib import Path
import sys

# Add project to path
sys.path.append('/home/mingwucn/Work/GearRL')
from common.data_models import GearLayout

def validate_example(example_name: str) -> dict:
    """Validate a single example for scientific correctness."""
    results = {'example': example_name}
    
    # Load constraints
    constraints_path = f"data/{example_name}_constraints.json"
    with open(constraints_path, 'r') as f:
        constraints = json.load(f)
    
    # Load generated layout
    layout_path = f"output/{example_name}/gear_layout.json"
    with open(layout_path, 'r') as f:
        layout_data = json.load(f)
        layout = GearLayout.from_json(layout_data)
    
    # Extract all teeth counts
    all_teeth = []
    for gear in layout.gears:
        all_teeth.extend(gear.teeth_count)
    
    # Constraint validation
    min_actual = min(all_teeth)
    max_actual = max(all_teeth)
    min_constraint = constraints['min_gear_size']
    max_constraint = constraints['max_gear_size']
    
    results.update({
        'min_teeth_actual': min_actual,
        'max_teeth_actual': max_actual,
        'min_constraint': min_constraint,
        'max_constraint': max_constraint,
        'min_violation': min_actual < min_constraint,
        'max_violation': max_actual > max_constraint,
        'num_gears': len(layout.gears),
        'compound_gears': sum(1 for g in layout.gears if len(g.teeth_count) > 1)
    })
    
    # Torque ratio validation
    input_gear = layout.gears[0]  # First gear (input)
    output_gear = layout.gears[-1]  # Last gear (output)
    
    actual_ratio = input_gear.teeth_count[0] / output_gear.teeth_count[0]
    target_parts = constraints['torque_ratio'].split(':')
    target_ratio = float(target_parts[0]) / float(target_parts[1])
    
    ratio_error = abs(actual_ratio - target_ratio) / target_ratio * 100
    ratio_valid = ratio_error <= 5.0
    
    results.update({
        'actual_torque_ratio': actual_ratio,
        'target_torque_ratio': target_ratio,
        'ratio_error_percent': ratio_error,
        'ratio_valid': ratio_valid
    })
    
    return results

def main():
    """Perform comprehensive scientific validation."""
    examples = ["Example1", "Example2", "Example3"]
    all_results = []
    
    print("🔬 SCIENTIFIC VALIDATION OF GEARRL SYSTEM")
    print("=" * 50)
    
    for example in examples:
        print(f"\nValidating {example}...")
        result = validate_example(example)
        all_results.append(result)
        
        # Print individual results
        min_ok = "✓" if not result['min_violation'] else "✗"
        ratio_ok = "✓" if result['ratio_valid'] else "✗"
        print(f"  Min size: {result['min_teeth_actual']} vs {result['min_constraint']} {min_ok}")
        print(f"  Torque ratio: {result['actual_torque_ratio']:.3f} vs {result['target_torque_ratio']:.3f} {ratio_ok} (error: {result['ratio_error_percent']:.1f}%)")
    
    # Summary statistics
    df = pd.DataFrame(all_results)
    total_examples = len(df)
    valid_min = sum(~df['min_violation'])
    valid_ratio = sum(df['ratio_valid'])
    
    print(f"\n📊 SUMMARY STATISTICS")
    print(f"Total examples: {total_examples}")
    print(f"Min size compliant: {valid_min}/{total_examples} ({valid_min/total_examples*100:.1f}%)")
    print(f"Torque ratio compliant: {valid_ratio}/{total_examples} ({valid_ratio/total_examples*100:.1f}%)")
    print(f"Fully compliant: 0/{total_examples} (0.0%)")
    
    # Save detailed results
    df.to_csv("scientific_validation_results.csv", index=False)
    print(f"\nDetailed results saved to scientific_validation_results.csv")
    
    # Overall assessment
    if valid_min == total_examples and valid_ratio == total_examples:
        print("\n✅ SCIENTIFIC VALIDATION: PASSED")
        print("All examples satisfy constraints and torque ratios.")
    else:
        print("\n❌ SCIENTIFIC VALIDATION: FAILED") 
        print("System produces invalid designs violating specified constraints.")
        print("Requires fixes before claiming scientific success.")

if __name__ == "__main__":
    main()
