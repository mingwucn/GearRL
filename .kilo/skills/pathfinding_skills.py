"""
Pathfinding skills for GearRL system implementing A* algorithm and centerline smoothing.
"""

import math
from heapq import heappop, heappush
from typing import List, Tuple, Dict, Any, Optional
from common.data_models import Point


class AStarPathfinder:
    """Implements A* pathfinding algorithm for gear placement."""
    
    def __init__(self, step_size: float = 0.5, boundary_margin: float = 5.0):
        self.step_size = step_size
        self.boundary_margin = boundary_margin
    
    def find_path(self, start: Point, goal: Point, boundaries: List[Point]) -> Optional[List[Point]]:
        """
        Find shortest path between start and goal using A* algorithm.
        
        Args:
            start: Starting point
            goal: Goal point  
            boundaries: Boundary polygon points
            
        Returns:
            List of points representing the path, or None if no path found
        """
        if not self._is_valid_point(start, boundaries, self.boundary_margin):
            return None
        if not self._is_valid_point(goal, boundaries, self.boundary_margin):
            return None
            
        open_set = [(0.0, (start.x, start.y))]
        came_from = {}
        g_score = {(round(start.x, 4), round(start.y, 4)): 0.0}
        
        while open_set:
            current_f, current_coords = heappop(open_set)
            current_x, current_y = current_coords
            current_key = (round(current_x, 4), round(current_y, 4))
            
            # Check if we're close enough to goal
            if self._distance((current_x, current_y), (goal.x, goal.y)) < self.step_size:
                return self._reconstruct_path(came_from, Point(x=current_x, y=current_y))
            
            neighbors = self._get_neighbors(Point(x=current_x, y=current_y), goal, boundaries)
            for neighbor in neighbors:
                tentative_g_score = g_score.get(current_key, float('inf')) + self._distance(
                    (current_x, current_y), (neighbor.x, neighbor.y)
                )
                neighbor_key = (round(neighbor.x, 4), round(neighbor.y, 4))
                
                if tentative_g_score < g_score.get(neighbor_key, float('inf')):
                    came_from[neighbor_key] = Point(x=current_x, y=current_y)
                    g_score[neighbor_key] = tentative_g_score
                    f_score = tentative_g_score + self._distance((neighbor.x, neighbor.y), (goal.x, goal.y))
                    heappush(open_set, (f_score, (neighbor.x, neighbor.y)))
                    
        return None
    
    def _get_neighbors(self, current: Point, goal: Point, boundaries: List[Point]) -> List[Point]:
        """Get valid neighboring points for current position."""
        neighbors = []
        
        # Check direct line of sight to goal
        if self._has_line_of_sight(current, goal, boundaries):
            neighbors.append(goal)
            return neighbors
            
        # Generate 8-directional neighbors
        for dx in [-self.step_size, 0, self.step_size]:
            for dy in [-self.step_size, 0, self.step_size]:
                if dx == 0 and dy == 0:
                    continue
                neighbor = Point(x=current.x + dx, y=current.y + dy)
                if self._is_valid_point(neighbor, boundaries, self.boundary_margin):
                    neighbors.append(neighbor)
                    
        return neighbors
    
    def _is_valid_point(self, point: Point, boundaries: List[Point], margin: float) -> bool:
        """Check if point is inside boundary and has sufficient clearance."""
        if not self._is_point_inside_polygon(point, boundaries):
            return False
        if self._distance_to_boundary(point, boundaries) < margin:
            return False
        return True
    
    def _has_line_of_sight(self, p1: Point, p2: Point, boundaries: List[Point]) -> bool:
        """Check if there's clear line of sight between two points."""
        dist = self._distance((p1.x, p1.y), (p2.x, p2.y))
        if dist < self.step_size:
            return True
            
        num_checks = int(dist / self.step_size)
        if num_checks == 0:
            return True
            
        dx = (p2.x - p1.x) / num_checks
        dy = (p2.y - p1.y) / num_checks
        
        for i in range(1, num_checks):
            intermediate = Point(x=p1.x + i * dx, y=p1.y + i * dy)
            if not self._is_valid_point(intermediate, boundaries, self.boundary_margin):
                return False
        return True
    
    def _reconstruct_path(self, came_from: Dict[Tuple[float, float], Point], current: Point) -> List[Point]:
        """Reconstruct path from came_from dictionary."""
        path = [current]
        current_key = (round(current.x, 4), round(current.y, 4))
        
        while current_key in came_from:
            current_point = came_from[current_key]
            path.append(current_point)
            current_key = (round(current_point.x, 4), round(current_point.y, 4))
            
        path.reverse()
        return path
    
    # Geometry helper methods
    def _is_point_inside_polygon(self, point: Point, polygon: List[Point]) -> bool:
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
    
    def _distance_to_boundary(self, point: Point, boundaries: List[Point]) -> float:
        """Calculate minimum distance from point to boundary edges."""
        min_dist = float('inf')
        n = len(boundaries)
        
        for i in range(n):
            p1 = boundaries[i]
            p2 = boundaries[(i + 1) % n]
            dist = self._point_to_segment_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                
        return min_dist
    
    def _point_to_segment_distance(self, p: Point, v: Point, w: Point) -> float:
        """Calculate distance from point to line segment."""
        l2 = (v.x - w.x)**2 + (v.y - w.y)**2
        if l2 == 0.0:
            return math.sqrt((p.x - v.x)**2 + (p.y - v.y)**2)
            
        t = max(0.0, min(1.0, ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2))
        projection_x = v.x + t * (w.x - v.x)
        projection_y = v.y + t * (w.y - v.y)
        return math.sqrt((p.x - projection_x)**2 + (p.y - projection_y)**2)
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


class PathSmoother:
    """Smooths paths by pushing them away from boundaries."""
    
    def __init__(self, smoothing_iterations: int = 500, smoothing_amount: float = 0.2):
        self.smoothing_iterations = smoothing_iterations
        self.smoothing_amount = smoothing_amount
    
    def smooth_path(self, path: List[Point], boundaries: List[Point]) -> List[Point]:
        """
        Smooth path by iteratively pushing points away from boundaries.
        
        Args:
            path: Original path to smooth
            boundaries: Boundary polygon points
            
        Returns:
            Smoothed path with better centering
        """
        if len(path) < 3:
            return path
            
        smoothed_path = [path[0]]  # Keep start fixed
        smoothed_path.extend(path[1:-1])  # Copy middle points
        smoothed_path.append(path[-1])  # Keep end fixed
        
        # Iteratively smooth interior points
        for _ in range(self.smoothing_iterations):
            new_path = [smoothed_path[0]]
            
            for i in range(1, len(smoothed_path) - 1):
                point = smoothed_path[i]
                closest_boundary_point = self._get_closest_boundary_point(point, boundaries)
                
                # Calculate repulsion vector
                repulsion_x = point.x - closest_boundary_point.x
                repulsion_y = point.y - closest_boundary_point.y
                
                # Normalize repulsion vector
                magnitude = math.sqrt(repulsion_x**2 + repulsion_y**2)
                if magnitude < 1e-6:
                    unit_x, unit_y = 0.0, 0.0
                else:
                    unit_x = repulsion_x / magnitude
                    unit_y = repulsion_y / magnitude
                
                # Move point along repulsion vector
                new_x = point.x + unit_x * self.smoothing_amount
                new_y = point.y + unit_y * self.smoothing_amount
                new_point = Point(x=new_x, y=new_y)
                
                # Only update if new point stays inside boundary
                if self._is_point_inside_polygon(new_point, boundaries):
                    new_path.append(new_point)
                else:
                    new_path.append(point)
                    
            new_path.append(smoothed_path[-1])
            smoothed_path = new_path
            
        return smoothed_path
    
    def _get_closest_boundary_point(self, point: Point, boundaries: List[Point]) -> Point:
        """Find closest point on boundary to given point."""
        min_dist = float('inf')
        closest_point = Point(x=0.0, y=0.0)
        
        for i in range(len(boundaries)):
            p1 = boundaries[i]
            p2 = boundaries[(i + 1) % len(boundaries)]
            proj_point, dist = self._get_projection_and_distance(point, p1, p2)
            if dist < min_dist:
                min_dist = dist
                closest_point = proj_point
                
        return closest_point
    
    def _get_projection_and_distance(self, p: Point, v: Point, w: Point) -> Tuple[Point, float]:
        """Get projection of point onto line segment and distance."""
        l2 = (v.x - w.x)**2 + (v.y - w.y)**2
        if l2 == 0.0:
            return v, math.sqrt((p.x - v.x)**2 + (p.y - v.y)**2)
            
        t = max(0.0, min(1.0, ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2))
        projection_x = v.x + t * (w.x - v.x)
        projection_y = v.y + t * (w.y - v.y)
        projection = Point(x=projection_x, y=projection_y)
        dist = math.sqrt((p.x - projection_x)**2 + (p.y - projection_y)**2)
        return projection, dist
    
    def _is_point_inside_polygon(self, point: Point, polygon: List[Point]) -> bool:
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