"""
GearRL Reusable Skills and Rules - Usage Guide

This guide explains how to use the reusable skills and rules in the .kilo folder.
All components are designed to be modular, composable, and easy to integrate.

Table of Contents:
1. Skills Overview
2. Rules Overview  
3. Basic Usage Patterns
4. Advanced Integration Examples
5. Best Practices

---

## 1. Skills Overview

Skills are stateless utility classes that encapsulate specific functionality.

### Data Model Skills (.kilo/skills/data_model_skills.py)
- Handle serialization, deserialization, and transformation of data models
- Convert between different coordinate systems and formats
- Validate data model integrity

### Preprocessing Skills (.kilo/skills/preprocessing_skills.py)  
- Process input images and constraints
- Normalize coordinates to consistent scale
- Detect shafts and boundaries using computer vision

### Pathfinding Skills (.kilo/skills/pathfinding_skills.py)
- Implement A* pathfinding algorithm for collision-free paths
- Provide centerline smoothing for optimal gear placement
- Handle boundary margin constraints

### Gear Generation Skills (.kilo/skills/gear_generation_skills.py)
- Create simple and compound gears with proper meshing
- Handle both single and multiple teeth counts per shaft
- Ensure gears meet size and meshing constraints

### Physics Validation Skills (.kilo/skills/physics_validation_skills.py)
- Comprehensive physics validation for gear layouts
- Check collisions, boundary containment, torque ratios
- Generate detailed validation reports

### RL Environment Skills (.kilo/skills/rl_environment_skills.py)
- State representation for reinforcement learning
- Reward shaping based on physical constraints
- Observation space management

### Visualization Skills (.kilo/skills/visualization_skills.py)
- Matplotlib-based rendering of gear trains
- Support for compound gear visualization
- Publication-quality output generation

---

## 2. Rules Overview

Rules are pure functions that validate specific constraints and return boolean results.

### Constraint Validation Rules (.kilo/rules/constraint_validation_rules.py)
- Validate all system-level constraints
- Check torque ratio, mass-space ratio, boundary margins
- Return detailed validation results

### Gear Placement Rules (.kilo/rules/gear_placement_rules.py)
- Validate minimum and maximum gear size constraints  
- Check gear spacing and positioning
- Ensure proper clearance between gears

### Meshing Compatibility Rules (.kilo/rules/meshing_compatibility_rules.py)
- Validate gear meshing compatibility
- Check proper meshing distances and alignment
- Ensure smooth power transmission

### Boundary Margin Rules (.kilo/rules/boundary_margin_rules.py)
- Validate safe clearance from boundaries
- Calculate effective placement zones
- Handle complex boundary geometries

### Torque Ratio Rules (.kilo/rules/torque_ratio_rules.py)
- Parse and validate torque ratio specifications
- Calculate actual vs target torque ratios
- Handle tolerance-based validation

### Success/Failure Rules (.kilo/rules/success_failure_rules.py)
- Determine complete success conditions
- Identify partial success scenarios
- Define failure modes and recovery strategies

---

## 3. Basic Usage Patterns

### Importing Skills and Rules
```python
# Add .kilo to Python path
import sys
sys.path.append('.kilo')

# Import specific skills
from skills.data_model_skills import DataModelSkill
from skills.gear_generation_skills import GearGenerator

# Import specific rules  
from rules.constraint_validation_rules import ConstraintValidationRules
from rules.torque_ratio_rules import TorqueRatioRules
```

### Using Data Model Skills
```python
# Serialize system definition
system = SystemDefinition(...)  # Your system definition
serialized = DataModelSkill.serialize_system_definition(system)

# Deserialize gear layout
layout_data = {"gears": [...]}  # JSON data
layout = DataModelSkill.deserialize_gear_layout(layout_data)

# Transform coordinates
normalized_points = [(x, y) for x, y in pixel_coords]
transformed = DataModelSkill.transform_coordinates(
    normalized_points, scale, offset_x, offset_y
)
```

### Using Gear Generation Skills
```python
# Create gear generator
generator = GearGenerator(module=1.0)

# Create simple gear
simple_gear = generator.create_simple_gear(
    gear_id="input", 
    center=Point(10, 20), 
    teeth_count=25
)

# Create compound gear  
compound_gear = generator.create_compound_gear(
    gear_id="intermediate",
    center=Point(30, 40),
    driven_teeth=20,
    driving_teeth=15
)

# Get meshing distance
distance = generator.get_meshing_distance(25, 20)  # Between 25-tooth and 20-tooth gears
```

### Using Physics Validation Skills
```python
# Create validator
validator = PhysicsValidationSkill()

# Validate layout
report = validator.validate_layout(gear_layout, system_definition)

# Check validity
if report.is_valid:
    print("Layout is valid!")
else:
    print("Validation errors:")
    for error in report.errors:
        print(f"  - {error}")
```

### Using Constraint Validation Rules
```python
# Validate torque ratio constraint
torque_valid = ConstraintValidationRules.validate_torque_ratio_constraint(
    gear_layout, system_definition
)

# Validate all constraints
all_valid = ConstraintValidationRules.validate_all_constraints(
    gear_layout, system_definition
)
```

---

## 4. Advanced Integration Examples

### Complete Pipeline Integration
```python
import sys
sys.path.append('.kilo')

from skills.preprocessing_skills import ImageProcessor
from skills.pathfinding_skills import PathfinderSkill  
from skills.gear_generation_skills import GearGenerator
from skills.physics_validation_skills import PhysicsValidationSkill
from rules.constraint_validation_rules import ConstraintValidationRules

def generate_valid_gear_train(input_image, constraints_file):
    """Complete pipeline for generating valid gear trains."""
    
    # 1. Preprocess input
    processor = ImageProcessor()
    intermediate_data = processor.process_input(
        input_image, constraints_file, "intermediate.json"
    )
    
    # 2. Find optimal path
    pathfinder = PathfinderSkill()
    path = pathfinder.find_centerline_path("intermediate.json")
    
    # 3. Generate initial gear layout (simplified)
    generator = GearGenerator(module=1.0)
    # ... gear generation logic ...
    
    # 4. Validate layout
    validator = PhysicsValidationSkill()
    report = validator.validate_layout(gear_layout, system_definition)
    
    # 5. Check constraint compliance
    constraints_valid = ConstraintValidationRules.validate_all_constraints(
        gear_layout, system_definition
    )
    
    if report.is_valid and constraints_valid:
        return gear_layout, report
    else:
        raise ValueError("Generated layout violates constraints")
```

### Reinforcement Learning Integration
```python
from skills.rl_environment_skills import StateRepresentationSkill
from skills.reward_shaping_skills import RewardShapingSkill  # If available

class GearRLEnvironment:
    def __init__(self, config):
        self.state_skill = StateRepresentationSkill(config)
        self.reward_skill = RewardShapingSkill(config)
        self.validator = PhysicsValidationSkill()
        
    def step(self, action):
        # ... execute action ...
        
        # Get observation
        observation = self.state_skill.get_observation_from_layout(layout, system)
        
        # Calculate reward
        validation_report = self.validator.validate_layout(layout, system)
        reward = self.reward_skill.calculate_reward(validation_report, system.constraints)
        
        # Check done condition
        done = not validation_report.is_valid or self.check_success_condition(layout)
        
        return observation, reward, done, {}
```

---

## 5. Best Practices

### Error Handling
- Always validate inputs before processing
- Use try-catch blocks for file operations and external dependencies
- Return meaningful error messages with context

### Performance Optimization  
- Cache computed values when possible
- Use vectorized operations for geometry calculations
- Avoid unnecessary object creation in hot paths

### Testing Strategy
- Test each skill in isolation with unit tests
- Test rule combinations with integration tests  
- Validate against known good solutions
- Include edge cases (minimum/maximum values, boundary conditions)

### Extensibility
- Follow single responsibility principle
- Use composition over inheritance
- Keep interfaces consistent across skills
- Document expected inputs and outputs clearly

### Integration Guidelines
- Skills should be stateless and composable
- Rules should be pure functions with no side effects  
- Handle both simple and compound gear scenarios
- Maintain backward compatibility when extending

---

## Common Issues and Solutions

### Issue: ModuleNotFoundError for '.kilo'
**Solution**: Add the project root to Python path:
```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.kilo'))
```

### Issue: Coordinate System Mismatches  
**Solution**: Always use normalized coordinates in the range [-50, +50] for internal processing. Use DataModelSkill for coordinate transformations.

### Issue: Constraint Violations in Generated Layouts
**Solution**: Always validate layouts using PhysicsValidationSkill before considering them valid. Use ConstraintValidationRules for specific constraint checks.

### Issue: Performance Bottlenecks in Pathfinding
**Solution**: Use appropriate step sizes and margin values. Consider caching pathfinding results for repeated queries.

---

## Example: Complete Validation Workflow

```python
import sys
sys.path.append('.kilo')

from skills.data_model_skills import DataModelSkill
from skills.physics_validation_skills import PhysicsValidationSkill  
from rules.constraint_validation_rules import ConstraintValidationRules
from common.data_models import SystemDefinition, GearLayout

# Load data
with open('system.json', 'r') as f:
    system_data = json.load(f)
    
with open('layout.json', 'r') as f:
    layout_data = json.load(f)

# Deserialize
system = SystemDefinition.from_json(system_data)
layout = GearLayout.from_json(layout_data)

# Comprehensive validation
validator = PhysicsValidationSkill()
physics_report = validator.validate_layout(layout, system)

constraint_valid = ConstraintValidationRules.validate_all_constraints(layout, system)

if physics_report.is_valid and constraint_valid:
    print("✅ Layout is scientifically valid!")
    print(f"   Physics violations: {len(physics_report.errors)}")
else:
    print("❌ Layout has validation issues:")
    if not physics_report.is_valid:
        print(f"   Physics errors: {physics_report.errors}")
    if not constraint_valid:
        print("   Constraint validation failed")
```

This guide provides a comprehensive overview of how to effectively use the reusable skills and rules in the GearRL system. All components are designed to work together seamlessly while maintaining modularity and extensibility.
