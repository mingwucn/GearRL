import math
from typing import List, Tuple
from common.data_models import GearLayout, SystemDefinition, ValidationReport, Gear, Point, Constraints

class FixedPhysicsValidator:
    @staticmethod
    def check_layout(layout: GearLayout, system: SystemDefinition) -> ValidationReport:
        """
        Validates a gear layout against physical constraints in normalized coordinates.
        
        Args:
            layout: GearLayout containing all gears in the system
            system: SystemDefinition containing boundary and constraints
            
        Returns:
            ValidationReport with validation results
        """
        report = ValidationReport(is_valid=True)
        
        # 1. Check gear collisions
        collision_errors = FixedPhysicsValidator._check_gear_collisions(layout.gears)
        report.errors.extend(collision_errors)
        
        # 2. Check boundary containment
        boundary_errors = FixedPhysicsValidator._check_boundary_containment(
            layout.gears, 
            system.boundary.points,
            system.constraints.boundary_margin
        )
        report.errors.extend(boundary_errors)
        
        # 3. Check gear size constraints
        size_errors = FixedPhysicsValidator._check_gear_sizes(
            layout.gears,
            system.constraints.min_gear_size,
            system.constraints.max_gear_size
        )
        report.errors.extend(size_errors)
        
        # 4. Check torque ratio
        torque_error = FixedPhysicsValidator._check_torque_ratio(
            layout.gears,
            system.input_shaft,
            system.output_shaft,
            system.constraints.torque_ratio
        )
        if torque_error:
            report.errors.append(torque_error)
            
        # Set overall validity
        report.is_valid = len(report.errors) == 0
        
        return report

    @staticmethod
    def _get_gear_diameter(gear) -> float:
        """Get diameter from gear object (handles both Gear and GearSet)."""
        if hasattr(gear, 'diameters'):
            return gear.diameters[0]
        elif hasattr(gear, 'diameter'):
            return gear.diameter
        else:
            # Calculate from teeth_count and module
            return gear.teeth_count[0] * gear.module

    @staticmethod
    def _check_gear_collisions(gears: List) -> List[str]:
        """Check for collisions between gears using circle-circle intersection"""
        errors = []
        for i, gear1 in enumerate(gears):
            for j, gear2 in enumerate(gears[i+1:], start=i+1):
                # Calculate Euclidean distance between centers
                dx = gear1.center.x - gear2.center.x
                dy = gear1.center.y - gear2.center.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                # Calculate sum of radii using correct diameter accessor
                d1 = FixedPhysicsValidator._get_gear_diameter(gear1)
                d2 = FixedPhysicsValidator._get_gear_diameter(gear2)
                min_dist = (d1/2) + (d2/2)
                
                # Add tolerance for floating point precision
                if dist < min_dist - 1e-5:
                    errors.append(
                        f"Gear collision between gear {i} and gear {j}: "
                        f"Distance {dist:.4f} < minimum required {min_dist:.4f}"
                    )
        return errors

    @staticmethod  
    def _check_boundary_containment(
        gears: List,
        boundary_points: List[Point],
        margin: float
    ) -> List[str]:
        """Check all gears are within boundary with specified margin"""
        errors = []
        for i, gear in enumerate(gears):
            # Check if gear center is inside boundary
            if not FixedPhysicsValidator._is_point_in_polygon(gear.center, boundary_points):
                errors.append(f"Gear {i} center outside boundary polygon")
                continue
                
            # Calculate required clearance (radius + margin)
            diameter = FixedPhysicsValidator._get_gear_diameter(gear)
            required_clearance = (diameter / 2) + margin
            
            # Check distance to boundary edges
            min_dist = FixedPhysicsValidator._min_distance_to_boundary(gear.center, boundary_points)
            if min_dist < required_clearance:
                errors.append(
                    f"Gear {i} too close to boundary: "
                    f"Distance {min_dist:.4f} < required {required_clearance:.4f}"
                )
        return errors

    @staticmethod
    def _check_gear_sizes(
        gears: List,
        min_size: int,
        max_size: int
    ) -> List[str]:
        """Validate gear sizes against constraints"""
        errors = []
        for i, gear in enumerate(gears):
            teeth = gear.teeth_count[0] if isinstance(gear.teeth_count, list) else gear.teeth_count
            if teeth < min_size:
                errors.append(
                    f"Gear {i} too small: {teeth} teeth < minimum {min_size}"
                )
            if teeth > max_size:
                errors.append(
                    f"Gear {i} too large: {teeth} teeth > maximum {max_size}"
                )
        return errors

    @staticmethod
    def _check_torque_ratio(
        gears: List,
        input_shaft: Point,
        output_shaft: Point,
        target_ratio: str
    ) -> str:
        """Validate torque ratio (simplified implementation)"""
        if target_ratio == "free":
            return ""
            
        try:
            # Find input and output gears (nearest to shafts)
            input_gear = min(gears, key=lambda g: 
                math.hypot(g.center.x - input_shaft.x, g.center.y - input_shaft.y))
            output_gear = min(gears, key=lambda g: 
                math.hypot(g.center.x - output_shaft.x, g.center.y - output_shaft.y))
                
            # Skip if we didn't find distinct gears
            if input_gear is output_gear:
                return "Cannot determine torque ratio - input and output gears are the same"
                
            # Convert ratio string to float (e.g., "2:1" -> 2.0)
            ratio_parts = target_ratio.split(":")
            if len(ratio_parts) != 2:
                return f"Invalid torque ratio format: {target_ratio}"
                
            try:
                target_value = float(ratio_parts[0]) / float(ratio_parts[1])
            except (ValueError, ZeroDivisionError):
                return f"Invalid torque ratio format: {target_ratio}"
                
            # Calculate actual ratio
            input_teeth = input_gear.teeth_count[0] if isinstance(input_gear.teeth_count, list) else input_gear.teeth_count
            output_teeth = output_gear.teeth_count[0] if isinstance(output_gear.teeth_count, list) else output_gear.teeth_count
            actual_ratio = input_teeth / output_teeth
            
            # Check with tolerance
            if not math.isclose(actual_ratio, target_value, rel_tol=0.05):
                return (
                    f"Torque ratio mismatch: actual {actual_ratio:.2f} "
                    f"!= target {target_value:.2f}"
                )
        except Exception as e:
            return f"Torque ratio validation error: {str(e)}"
            
        return ""

    # ... (rest of helper methods remain the same)
    
    @staticmethod
    def _is_point_in_polygon(point: Point, polygon: List[Point]) -> bool:
        """Ray casting algorithm for point-in-polygon test"""
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if point.y > min(p1y, p2y):
                if point.y <= max(p1y, p2y):
                    if point.x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    @staticmethod
    def _min_distance_to_boundary(point: Point, boundary: List[Point]) -> float:
        """Calculate minimum distance from point to boundary edges"""
        min_dist = float('inf')
        n = len(boundary)
        
        # First check distance to all vertices
        for vertex in boundary:
            dx = point.x - vertex.x
            dy = point.y - vertex.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < min_dist:
                min_dist = dist
        
        # Then check distance to edges
        for i in range(n):
            p1 = boundary[i]
            p2 = boundary[(i + 1) % n]
            dist = FixedPhysicsValidator._point_to_line_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist

    @staticmethod
    def _point_to_line_distance(point: Point, line_p1: Point, line_p2: Point) -> float:
        """Calculate distance from point to line segment"""
        # Vector from line_p1 to line_p2
        line_vec = Point(line_p2.x - line_p1.x, line_p2.y - line_p1.y)
        # Vector from line_p1 to point
        point_vec = Point(point.x - line_p1.x, point.y - line_p1.y)
        
        # Length of line segment squared
        line_len_sq = line_vec.x**2 + line_vec.y**2
        
        # Dot product
        dot = point_vec.x * line_vec.x + point_vec.y * line_vec.y
        
        # Calculate projection
        if line_len_sq == 0:
            return math.hypot(point_vec.x, point_vec.y)
            
        t = max(0, min(1, dot / line_len_sq))
        
        # Projection point
        proj = Point(
            line_p1.x + t * line_vec.x,
            line_p1.y + t * line_vec.y
        )
        
        # Distance to projection point
        return math.hypot(point.x - proj.x, point.y - proj.y)
