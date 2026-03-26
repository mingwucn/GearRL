#!/bin/bash
# Fixed GearRL Run Script with Scientific Validity

set -e  # Exit on any error

echo "🚀 Starting Fixed GearRL Scientific Validation"
echo "============================================"

# Create output directories
mkdir -p models output_eval_fixed

# Function to run training and evaluation for an example
run_example() {
    local example=$1
    echo ""
    echo "🔧 Processing $example..."
    
    # Train model (reduced episodes for demo)
    echo "   Training model..."
    python3 fixed_train.py \
        --config_path env_config_${example}.json \
        --episodes 100 \
        --max_steps_per_episode 8 \
        --output_dir models \
        --log_interval 20
    
    # Evaluate model
    echo "   Evaluating model..."
    python3 fixed_evaluate.py \
        --model_path models/ppo_gear_placer_fixed.pt \
        --config_path env_config_${example}.json \
        --output_dir output_eval_fixed
    
    # Validate results
    echo "   Validating scientific correctness..."
    python3 validate_results.py output_eval_fixed/${example}_eval/evaluation_gear_layout.json data/${example}_constraints.json
}

# Create validation script
cat > validate_results.py << 'VALIDATE_PY'
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

sys.path.append('.')

from common.data_models import GearLayout, SystemDefinition, Boundary, Point, Constraints
from physics_validator.validator import PhysicsValidator

def main():
    layout_path = sys.argv[1]
    constraints_path = sys.argv[2]
    
    # Load layout
    with open(layout_path, 'r') as f:
        layout_data = json.load(f)
    layout = GearLayout.from_json(layout_data)
    
    # Load constraints and create system definition
    with open(constraints_path, 'r') as f:
        constraints_data = json.load(f)
    
    # Extract example name to get processed data
    example_name = Path(constraints_path).stem.replace('_constraints', '')
    processed_path = f"data/intermediate/{example_name}_processed.json"
    
    with open(processed_path, 'r') as f:
        processed_data = json.load(f)['normalized_space']
    
    system = SystemDefinition(
        boundary=Boundary(points=[Point(p[0], p[1]) for p in processed_data['boundaries']]),
        input_shaft=Point(processed_data['input_shaft']['x'], processed_data['input_shaft']['y']),
        output_shaft=Point(processed_data['output_shaft']['x'], processed_data['output_shaft']['y']),
        constraints=Constraints.from_json(constraints_data)
    )
    
    # Validate
    validator = PhysicsValidator()
    report = validator.check_layout(layout, system)
    
    print(f"✅ Layout is valid: {report.is_valid}")
    if not report.is_valid:
        print("❌ Validation errors:")
        for error in report.errors:
            print(f"   - {error}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
VALIDATE_PY

chmod +x validate_results.py

# Run all examples
examples=("example1" "example2" "example3")

for example in "${examples[@]}"; do
    run_example $example
done

echo ""
echo "📊 Final Scientific Validation Results"
echo "===================================="

# Check all validation reports
all_valid=true
for example in "${examples[@]}"; do
    report_file="output_eval_fixed/${example}_eval/validation_report.json"
    if [ -f "$report_file" ]; then
        is_valid=$(python3 -c "import json; print(json.load(open('$report_file'))['is_valid'])")
        if [ "$is_valid" != "True" ]; then
            all_valid=false
            echo "❌ ${example}: INVALID"
        else
            echo "✅ ${example}: VALID"
        fi
    else
        echo "❓ ${example}: No validation report"
        all_valid=false
    fi
done

if [ "$all_valid" = true ]; then
    echo ""
    echo "🎉 SUCCESS: All examples are scientifically valid!"
    echo "   - Constraint violations fixed"
    echo "   - Torque ratios correctly achieved"  
    echo "   - Proper constraint enforcement implemented"
else
    echo ""
    echo "⚠️  WARNING: Some examples still have issues"
    echo "   Please review validation reports for details"
fi

# Cleanup
rm validate_results.py

echo ""
echo "🔬 Scientific validation completed!"
