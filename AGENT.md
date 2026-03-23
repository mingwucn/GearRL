# GearRL System Architecture Patterns and Best Practices

## Modular Architecture Patterns

### 1. Component Separation
The GearRL system follows a strict separation of concerns pattern:

- **Data Models**: `common/data_models.py` - Pure data structures with serialization
- **Preprocessing**: `preprocessing/processor.py` - Image processing and coordinate normalization  
- **Pathfinding**: `pathfinding/finder.py` - A* pathfinding and centerline smoothing
- **Gear Generation**: `gear_generator/factory.py` - Gear creation and meshing logic
- **Physics Validation**: `physics_validator/validator.py` - Collision and constraint checking
- **RL Environment**: `geometry_env/` - Gymnasium-compatible environment
- **Visualization**: `visualization/renderer.py` - Matplotlib-based rendering

### 2. Skill-Based Architecture
Reusable skills are organized in `.kilo/skills/` directory:
- Each skill encapsulates specific functionality
- Skills are stateless and composable
- Follow single responsibility principle

### 3. Rule-Based Validation
Validation rules are organized in `.kilo/rules/` directory:
- Rules are pure functions with clear inputs/outputs
- Rules can be combined for complex validation scenarios
- Rules are testable in isolation

## Data Flow Pipeline Patterns

### 1. Linear Processing Pipeline
```
Input Image + Constraints 
    ↓
Preprocessing (coordinate normalization)
    ↓  
Pathfinding (A* + smoothing)
    ↓
Gear Generation (simple/compound gears)
    ↓
Physics Validation (collision, boundary, torque)
    ↓
RL Environment (state representation, reward)
    ↓
Visualization (matplotlib rendering)
```

### 2. State Management
- **SystemDefinition**: Immutable system constraints and geometry
- **GearLayout**: Current gear placement state
- **ValidationReport**: Validation results with error details
- **Observation Space**: RL state representation (5-dimensional)

### 3. Coordinate Systems
- **Pixel Space**: Original image coordinates
- **Normalized Space**: Transformed to [-50, 50] range for consistent processing
- **All components work in normalized space** for stability

## Configuration Management Patterns

### 1. Centralized Configuration
Configuration is passed as dictionaries to components:
```python
config = {
    "min_gear_teeth": 8,
    "max_gear_teeth": 40, 
    "module": 1.0,
    "clearance_margin": 1.0,
    "boundary_margin": 5.0
}
```

### 2. Constraint Definition
Constraints follow a consistent structure:
```json
{
    "torque_ratio": "2:1",      // or "free"
    "mass_space_ratio": 0.5,    // max mass per unit area
    "boundary_margin": 5.0,     // min distance from boundary
    "min_gear_size": 8,         // min teeth count
    "max_gear_size": 200        // max teeth count
}
```

### 3. JSON Serialization
All data models support bidirectional JSON serialization:
- `from_json()` class methods for deserialization
- `to_json()` instance methods for serialization
- Backward compatibility maintained for legacy formats

## Error Handling Patterns

### 1. Validation Reports
- `ValidationReport` contains `is_valid` boolean and `errors` list
- Errors are descriptive strings with specific failure reasons
- No exceptions thrown for validation failures (graceful degradation)

### 2. Defensive Programming
- Input validation at component boundaries
- Graceful handling of edge cases (empty inputs, invalid geometries)
- Meaningful error messages with context

### 3. Failure Recovery
- Invalid layouts return negative rewards in RL context
- Pathfinding falls back to shortest path if smoothing fails
- Gear generation uses closest valid tooth count when approximating diameter

## Testing and Validation Patterns

### 1. Unit Testing Structure
Tests are organized by component:
- `tests/test_data_models.py` - Data model serialization
- `tests/test_validator.py` - Physics validation
- `tests/test_finder.py` - Pathfinding algorithms  
- `tests/test_factory.py` - Gear generation
- `tests/integration/test_system.py` - End-to-end integration

### 2. Test Data Strategy
- Use realistic test cases from example datasets
- Include edge cases (minimum/maximum values, boundary conditions)
- Validate against known good solutions

### 3. Validation Metrics
Key metrics for evaluation:
- **Success Rate**: % of valid layouts generated
- **Constraint Satisfaction**: % meeting all constraints  
- **Torque Accuracy**: Deviation from target ratio
- **Space Efficiency**: Mass-space ratio utilization
- **Path Quality**: Clearance from boundaries

## Performance Optimization Patterns

### 1. Efficient Geometry Operations
- Ray casting for point-in-polygon tests
- Vectorized distance calculations
- Early termination in collision detection

### 2. Memory Management
- Avoid unnecessary object creation in hot paths
- Reuse computed values (caching where appropriate)
- Efficient data structures for spatial queries

### 3. Algorithm Selection
- A* for optimal pathfinding with heuristic guidance
- Ramer-Douglas-Peucker for boundary simplification
- Iterative smoothing for path centering

## Extensibility Patterns

### 1. Plugin Architecture
New skills and rules can be added without modifying core components:
- Drop new skill files in `.kilo/skills/`
- Add rule files in `.kilo/rules/`
- Components discover and use available skills/rules

### 2. Configuration-Driven Behavior
Behavior can be modified through configuration:
- Different reward weights for RL training
- Adjustable tolerance levels for validation
- Custom module sizes for gear generation

### 3. Interface Consistency
All components follow consistent interfaces:
- Standard method signatures
- Consistent error handling
- Uniform data format expectations

## Best Practices Summary

1. **Always validate inputs** before processing
2. **Use normalized coordinates** for all geometric operations  
3. **Maintain backward compatibility** in serialization formats
4. **Keep components stateless** when possible
5. **Write comprehensive unit tests** for each component
6. **Document assumptions** and limitations clearly
7. **Handle floating-point precision** issues with appropriate tolerances
8. **Use meaningful variable names** that reflect physical meaning
9. **Separate concerns** rigorously between components
10. **Profile performance** bottlenecks in geometry-heavy operations