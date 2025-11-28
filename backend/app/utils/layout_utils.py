"""Layout analysis and comparison utilities."""

from typing import Dict, Tuple, Optional, List
import numpy as np


class BoundingBox:
    """Represents a bounding box for an element."""
    
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    @property
    def right(self) -> float:
        return self.x + self.width
    
    @property
    def bottom(self) -> float:
        return self.y + self.height
    
    @property
    def center_x(self) -> float:
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        return self.y + self.height / 2
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "right": self.right,
            "bottom": self.bottom
        }
    
    def intersection(self, other: 'BoundingBox') -> Optional['BoundingBox']:
        """Calculate intersection with another bounding box."""
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        right = min(self.right, other.right)
        bottom = min(self.bottom, other.bottom)
        
        if right > x and bottom > y:
            return BoundingBox(x, y, right - x, bottom - y)
        return None
    
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union (IoU) with another box."""
        intersection = self.intersection(other)
        if not intersection:
            return 0.0
        
        intersection_area = intersection.area
        union_area = self.area + other.area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0


def calculate_spacing(element1: Dict, element2: Dict, direction: str = "auto") -> Dict:
    """
    Calculate spacing between two elements.
    
    Args:
        element1: First element with bounds
        element2: Second element with bounds
        direction: "horizontal", "vertical", or "auto"
    
    Returns:
        Dictionary with spacing information
    """
    box1 = BoundingBox(**element1)
    box2 = BoundingBox(**element2)
    
    # Horizontal spacing
    if box1.right < box2.x:
        h_spacing = box2.x - box1.right
        h_direction = "left-to-right"
    elif box2.right < box1.x:
        h_spacing = box1.x - box2.right
        h_direction = "right-to-left"
    else:
        h_spacing = 0
        h_direction = "overlapping"
    
    # Vertical spacing
    if box1.bottom < box2.y:
        v_spacing = box2.y - box1.bottom
        v_direction = "top-to-bottom"
    elif box2.bottom < box1.y:
        v_spacing = box1.y - box2.bottom
        v_direction = "bottom-to-top"
    else:
        v_spacing = 0
        v_direction = "overlapping"
    
    return {
        "horizontal_spacing": h_spacing,
        "horizontal_direction": h_direction,
        "vertical_spacing": v_spacing,
        "vertical_direction": v_direction,
        "primary_spacing": h_spacing if direction == "horizontal" or 
                          (direction == "auto" and h_spacing > v_spacing) else v_spacing
    }


def compare_dimensions(dims1: Dict, dims2: Dict, tolerance: int = 2) -> Dict:
    """
    Compare dimensions of two elements.
    
    Args:
        dims1: First element dimensions {width, height}
        dims2: Second element dimensions {width, height}
        tolerance: Acceptable difference in pixels
    
    Returns:
        Comparison results
    """
    width_diff = abs(dims1.get("width", 0) - dims2.get("width", 0))
    height_diff = abs(dims1.get("height", 0) - dims2.get("height", 0))
    
    return {
        "width_diff": width_diff,
        "height_diff": height_diff,
        "width_match": width_diff <= tolerance,
        "height_match": height_diff <= tolerance,
        "dimensions_match": width_diff <= tolerance and height_diff <= tolerance,
        "width_delta_percentage": (width_diff / dims1.get("width", 1)) * 100 if dims1.get("width") else 0,
        "height_delta_percentage": (height_diff / dims1.get("height", 1)) * 100 if dims1.get("height") else 0
    }


class LayoutAnalyzer:
    """Analyze and compare layout structures."""
    
    def __init__(self, spacing_tolerance: int = 2, dimension_tolerance: int = 2):
        """
        Initialize layout analyzer.
        
        Args:
            spacing_tolerance: Acceptable spacing difference in pixels
            dimension_tolerance: Acceptable dimension difference in pixels
        """
        self.spacing_tolerance = spacing_tolerance
        self.dimension_tolerance = dimension_tolerance
    
    def analyze_grid(self, elements: List[Dict]) -> Dict:
        """Analyze if elements form a grid layout."""
        if len(elements) < 2:
            return {"is_grid": False}
        
        # Get Y positions
        y_positions = [e.get("y", 0) for e in elements]
        unique_rows = len(set([round(y / 10) * 10 for y in y_positions]))  # Cluster similar Y values
        
        # Get X positions
        x_positions = [e.get("x", 0) for e in elements]
        unique_cols = len(set([round(x / 10) * 10 for x in x_positions]))
        
        return {
            "is_grid": unique_rows > 1 and unique_cols > 1,
            "estimated_rows": unique_rows,
            "estimated_columns": unique_cols,
            "total_elements": len(elements)
        }
    
    def detect_alignment(self, elements: List[Dict]) -> Dict:
        """Detect alignment patterns in elements."""
        if len(elements) < 2:
            return {"aligned": False}
        
        # Check left alignment
        left_edges = [e.get("x", 0) for e in elements]
        left_aligned = max(left_edges) - min(left_edges) <= self.spacing_tolerance
        
        # Check top alignment
        top_edges = [e.get("y", 0) for e in elements]
        top_aligned = max(top_edges) - min(top_edges) <= self.spacing_tolerance
        
        # Check center alignment (horizontal)
        center_x = [(e.get("x", 0) + e.get("width", 0) / 2) for e in elements]
        center_h_aligned = max(center_x) - min(center_x) <= self.spacing_tolerance
        
        # Check center alignment (vertical)
        center_y = [(e.get("y", 0) + e.get("height", 0) / 2) for e in elements]
        center_v_aligned = max(center_y) - min(center_y) <= self.spacing_tolerance
        
        return {
            "left_aligned": left_aligned,
            "top_aligned": top_aligned,
            "center_horizontal_aligned": center_h_aligned,
            "center_vertical_aligned": center_v_aligned,
            "has_alignment": any([left_aligned, top_aligned, center_h_aligned, center_v_aligned])
        }
    
    def calculate_spacing_consistency(self, elements: List[Dict], direction: str = "horizontal") -> Dict:
        """Calculate spacing consistency between elements."""
        if len(elements) < 3:
            return {"consistent": False, "spacing": []}
        
        # Sort elements by position
        key = "x" if direction == "horizontal" else "y"
        sorted_elements = sorted(elements, key=lambda e: e.get(key, 0))
        
        # Calculate spacings
        spacings = []
        for i in range(len(sorted_elements) - 1):
            spacing_info = calculate_spacing(sorted_elements[i], sorted_elements[i + 1], direction)
            spacings.append(spacing_info["primary_spacing"])
        
        if not spacings:
            return {"consistent": False, "spacing": []}
        
        # Check consistency
        avg_spacing = np.mean(spacings)
        max_deviation = max([abs(s - avg_spacing) for s in spacings])
        is_consistent = max_deviation <= self.spacing_tolerance
        
        return {
            "consistent": is_consistent,
            "spacing": spacings,
            "average_spacing": avg_spacing,
            "max_deviation": max_deviation,
            "tolerance": self.spacing_tolerance
        }
    
    def compare_layouts(self, layout1: Dict, layout2: Dict) -> Dict:
        """Compare two layout structures."""
        result = {
            "match": True,
            "differences": []
        }
        
        # Compare element counts
        count1 = layout1.get("element_count", 0)
        count2 = layout2.get("element_count", 0)
        if count1 != count2:
            result["match"] = False
            result["differences"].append({
                "type": "element_count",
                "figma": count1,
                "website": count2,
                "delta": abs(count1 - count2)
            })
        
        # Compare alignment
        align1 = layout1.get("alignment", {})
        align2 = layout2.get("alignment", {})
        for key in ["left_aligned", "top_aligned", "center_horizontal_aligned", "center_vertical_aligned"]:
            if align1.get(key) != align2.get(key):
                result["match"] = False
                result["differences"].append({
                    "type": f"alignment_{key}",
                    "figma": align1.get(key),
                    "website": align2.get(key)
                })
        
        return result
