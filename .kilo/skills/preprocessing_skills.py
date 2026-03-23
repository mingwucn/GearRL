"""
Preprocessing skills for GearRL system handling image processing and coordinate normalization.
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from common.data_models import Point


class ImageProcessor:
    """Handles image preprocessing for gear system detection."""
    
    @staticmethod
    def detect_shaft_centers(img: np.ndarray, 
                           shaft_colors: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int]]] = None) -> Dict[str, Optional[Point]]:
        """
        Detect input and output shaft centers from image using color-based segmentation.
        
        Args:
            img: Input BGR image
            shaft_colors: Dictionary mapping shaft names to HSV color ranges
                        Default: {'input': red, 'output': green}
                        
        Returns:
            Dictionary with shaft center points or None if not found
        """
        if shaft_colors is None:
            shaft_colors = {
                'input': ((0, 120, 70), (10, 255, 255)),  # Red
                'output': ((35, 120, 70), (85, 255, 255))  # Green
            }
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        shaft_centers = {}
        
        for shaft_name, (lower_hsv, upper_hsv) in shaft_colors.items():
            mask = cv2.inRange(hsv, np.array(lower_hsv), np.array(upper_hsv))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                center_x, center_y = ImageProcessor._get_contour_center(largest_contour)
                shaft_centers[shaft_name] = Point(x=float(center_x), y=float(center_y))
            else:
                shaft_centers[shaft_name] = None
                
        return shaft_centers
    
    @staticmethod
    def detect_boundary(img: np.ndarray, epsilon_factor: float = 0.001) -> List[Point]:
        """
        Detect and approximate boundary polygon from image.
        
        Args:
            img: Input BGR image
            epsilon_factor: Factor for contour approximation (Ramer-Douglas-Peucker)
            
        Returns:
            List of boundary points as Point objects
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
            
        largest_contour = max(contours, key=cv2.contourArea)
        approximated_points = ImageProcessor._approximate_contour(largest_contour, epsilon_factor)
        
        return [Point(x=float(p[0]), y=float(p[1])) for p in approximated_points]
    
    @staticmethod
    def _get_contour_center(contour: np.ndarray) -> Tuple[float, float]:
        """Calculate center of mass for a contour."""
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return (0.0, 0.0)
        cX = M["m10"] / M["m00"]
        cY = M["m01"] / M["m00"]
        return (cX, cY)
    
    @staticmethod
    def _approximate_contour(contour: np.ndarray, epsilon_factor: float = 0.001) -> List[List[int]]:
        """Approximate contour using Ramer-Douglas-Peucker algorithm."""
        epsilon = epsilon_factor * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        return approx.squeeze().tolist()


class CoordinateNormalizer:
    """Handles coordinate normalization and transformation."""
    
    @staticmethod
    def calculate_normalization_params(points: List[Point]) -> Dict[str, float]:
        """
        Calculate normalization parameters to fit all points in [-50, 50] range.
        
        Args:
            points: List of points to normalize
            
        Returns:
            Dictionary with scale, offset_x, offset_y parameters
        """
        if not points:
            return {'scale': 1.0, 'offset_x': 0.0, 'offset_y': 0.0}
            
        coords = np.array([[p.x, p.y] for p in points])
        min_x, min_y = np.min(coords, axis=0)
        max_x, max_y = np.max(coords, axis=0)
        
        # Scale to fit in 100x100 area centered at origin
        scale = 100.0 / max(max_x - min_x, max_y - min_y + 1e-8)
        offset_x = -((min_x + max_x) / 2.0) * scale
        offset_y = -((min_y + max_y) / 2.0) * scale
        
        return {
            'scale': float(scale),
            'offset_x': float(offset_x),
            'offset_y': float(offset_y)
        }
    
    @staticmethod
    def normalize_points(points: List[Point], params: Dict[str, float]) -> List[Point]:
        """
        Normalize list of points using given parameters.
        
        Args:
            points: List of points to normalize
            params: Normalization parameters (scale, offset_x, offset_y)
            
        Returns:
            List of normalized points
        """
        scale = params['scale']
        offset_x = params['offset_x']
        offset_y = params['offset_y']
        
        normalized = []
        for point in points:
            norm_x = point.x * scale + offset_x
            norm_y = point.y * scale + offset_y
            normalized.append(Point(x=norm_x, y=norm_y))
        return normalized
    
    @staticmethod
    def denormalize_points(points: List[Point], params: Dict[str, float]) -> List[Point]:
        """
        Denormalize list of points using given parameters.
        
        Args:
            points: List of normalized points
            params: Normalization parameters (scale, offset_x, offset_y)
            
        Returns:
            List of denormalized points
        """
        scale = params['scale']
        offset_x = params['offset_x']
        offset_y = params['offset_y']
        
        denormalized = []
        for point in points:
            orig_x = (point.x - offset_x) / scale
            orig_y = (point.y - offset_y) / scale
            denormalized.append(Point(x=orig_x, y=orig_y))
        return denormalized