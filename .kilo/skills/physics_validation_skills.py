"""
Physics validation skills for GearRL system handling collision detection, boundary checking, and torque validation.
"""

from typing import List, Dict, Any, Optional
import math
from common.data_models import GearLayout, SystemDefinition, ValidationReport, Gear, Point, Constraints


class PhysicsValidationSkill:
    """Comprehensive physics validation for gear layouts."""
    
    def validate_layout(self, layout: GearLayout, system: SystemDefinition) -> ValidationReport:
        """
        Validate gear layout against physical constraints in normalized coordinates.
        
        Args:
            layout: GearLayout containing all gears in the system
            system: SystemDefinition containing boundary and constraints
            
        Returns:
            Validation report with detailed error messages
        """
        report = ValidationReport(is_valid=True, errors=[])
        
        # Check gear collisions
        collision_errors = self._check_gear_collisions(layout.gears)
        report.errors.extend(collision_errors)
        
        # Check boundary containment
        boundary_errors = self._check_boundary_containment(
            layout.gears,
            system.boundary.points,
            system.constraints.boundary_margin
        )
        report.errors.extend(boundary_errors)
        
        # Check gear size constraints
        size_errors = self._check_gear_sizes(
            layout.gears,
            system.constraints.min_gear_size,
            system.constraints.max_gear_size
        )
        report.errors.extend(size_errors)
        
        # Check torque ratio
        torque_error = self._check_torque_ratio(
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
    
    def _check_gear_collisions(self, gears: List[Gear]) -> List[str]:
        """Check for collisions between gears using circle-circle intersection."""
        errors = []
        for i, gear1 in enumerate(gears):
            for j, gear2 in enumerate(gears[i+1:], start=i+1):
                # Get maximum radii for collision detection
                max_radius1 = max(d / 2.0 for d in gear1.diameters)
                max_radius2 = max(d / 2.0 for d in gear2.diameters)
                
                # Calculate Euclidean distance between centers
                dx = gear1.center.x - gear2.center.x
                dy = gear1.center.y - gear2.center.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                # Calculate sum of radii
                min_dist = max_radius1 + max_radius2
                
                # Add tolerance for floating point precision
                if dist < min_dist - 1e-5:
                    errors.append(
                        f"Gear collision between gear {i} and gear {j}: "
                        f"Distance {dist:.4f} < minimum required {min_dist:.4f}"
                    )
        return errors
    
    def _check_boundary_containment(
        self,
        gears: List[Gear],
        boundary_points: List[Point],
        margin: float
    ) -> List[str]:
        """Check all gears are within boundary with specified margin."""
        errors = []
        for i, gear in enumerate(gears):
            # Check if gear center is inside boundary
            if not self._is_point_in_polygon(gear.center, boundary_points):
                errors.append(f"Gear {i} center outside boundary polygon")
                continue
                
            # Get maximum radius of gear
            max_radius = max(d / 2.0 for d in gear.diameters)
            required_clearance = max_radius + margin
            
            # Check distance to boundary edges
            min_dist = self._min_distance_to_boundary(gear.center, boundary_points)
            if min_dist < required_clearance:
                errors.append(
                    f"Gear {i} too close to boundary: "
                    f"Distance {min_dist:.4f} < required {required_clearance:.4f}"
                )
        return errors
    
    def _check_gear_sizes(
        self,
        gears: List[Gear],
        min_size: int,
        max_size: int
    ) -> List[str]:
        """Validate gear sizes against constraints."""
        errors = []
        for i, gear in enumerate(gears):
            max_teeth = max(gear.teeth_count)
            min_teeth = min(gear.teeth_count)
            if min_teeth < min_size:
                errors.append(
                    f"Gear {i} too small: min teeth {min_teeth} < minimum {min_size}"
                )
            if max_teeth > max_size:
                errors.append(
                    f"Gear {i} too large: max teeth {max_teeth} > maximum {max_size}"
                )
        return errors
    
    def _check_torque_ratio(
        self,
        gears: List[Gear],
        input_shaft: Point,
        output_shaft: Point,
        target_ratio: str
    ) -> str:
        """Validate torque ratio (simplified implementation)."""
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
                
            # Calculate actual ratio (using first teeth count for both gears)
            actual_ratio = input_gear.teeth_count[0] / output_gear.teeth_count[0]
            
            # Check with tolerance
            if not math.isclose(actual_ratio, target_value, rel_tol=0.05):
                return (
                    f"Torque ratio mismatch: actual {actual_ratio:.2f} "
                    f"!= target {target_value:.2f}"
                )
        except Exception as e:
            return f"Torque ratio validation error: {str(e)}"
            
        return ""
    
    def _is_point_in_polygon(self, point: Point, polygon: List[Point]) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0].x, polygon[0].y
        
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if min(p1y, p2y) < point.y <= max(p1y, p2y):
                if point.x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (point.y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    
    def _min_distance_to_boundary(self, point: Point, boundary: List[Point]) -> float:
        """Calculate minimum distance from point to boundary edges."""
        min_dist = float('inf')
        n = len(boundary)
        
        for i in range(n):
            p1 = boundary[i]
            p2 = boundary[(i + 1) % n]
            dist = self._point_to_line_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist
    
    def _point_to_line_distance(self, point: Point, line_p1: Point, line_p2: Point) -> float:
        """Calculate distance from point to line segment."""
        line_vec_x = line_p2.x - line_p1.x
        line_vec_y = line_p2.y - line_p1.y
        point_vec_x = point.x - line_p1.x
        point_vec_y = point.y - line_p1.y
        
        line_len_sq = line_vec_x**2 + line_vec_y**2
        
        if line_len_sq == 0:
            return (point_vec_x**2 + point_vec_y**2)**0.5
            
        dot = point_vec_x * line_vec_x + point_vec_y * line_vec_y
        t = max(0.0, min(1.0, dot / line_len_sq))
        
        proj_x = line_p1.x + t * line_vec_x
        proj_y = line_p1.y + t * line_vec_y
        
        return ((point.x - proj_x)**2 + (point.y - proj_y)**2)**0.5