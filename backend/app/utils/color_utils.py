"""Color analysis and comparison utilities."""

import re
from typing import Tuple, List, Optional, Dict
import webcolors
from PIL import Image
import numpy as np
from colorsys import rgb_to_hsv, hsv_to_rgb


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def rgba_to_rgb(rgba: Tuple[int, int, int, int], background: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    """Convert RGBA to RGB by blending with background."""
    r, g, b, a = rgba
    alpha = a / 255.0
    return (
        int(r * alpha + background[0] * (1 - alpha)),
        int(g * alpha + background[1] * (1 - alpha)),
        int(b * alpha + background[2] * (1 - alpha))
    )


def color_distance(color1: Tuple[int, int, int], color2: Tuple[int, int, int], method: str = "euclidean") -> float:
    """
    Calculate distance between two colors.
    
    Methods:
    - euclidean: Simple RGB Euclidean distance
    - cie76: CIE76 Delta E (requires RGB to LAB conversion)
    - perceptual: Weighted RGB distance (approximates human perception)
    """
    if method == "euclidean":
        return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))
    elif method == "perceptual":
        # Weighted Euclidean (approximates perceptual difference)
        r_mean = (color1[0] + color2[0]) / 2
        r_diff = color1[0] - color2[0]
        g_diff = color1[1] - color2[1]
        b_diff = color1[2] - color2[2]
        
        return np.sqrt(
            (2 + r_mean / 256) * r_diff ** 2 +
            4 * g_diff ** 2 +
            (2 + (255 - r_mean) / 256) * b_diff ** 2
        )
    else:
        return color_distance(color1, color2, "euclidean")


def parse_css_color(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse CSS color string to RGB tuple."""
    color_str = color_str.strip().lower()
    
    # Hex color
    if color_str.startswith('#'):
        try:
            return hex_to_rgb(color_str)
        except:
            return None
    
    # RGB/RGBA
    rgb_match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)', color_str)
    if rgb_match:
        return tuple(int(x) for x in rgb_match.groups())
    
    # Named color
    try:
        return webcolors.name_to_rgb(color_str)
    except:
        pass
    
    return None


class ColorAnalyzer:
    """Analyze and compare colors from designs and websites."""
    
    def __init__(self, tolerance: int = 5):
        """
        Initialize color analyzer.
        
        Args:
            tolerance: Maximum acceptable color distance (Delta E)
        """
        self.tolerance = tolerance
    
    def extract_dominant_colors(self, image_path: str, num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """Extract dominant colors from an image."""
        try:
            from extcolors import extract_from_path
            colors, _ = extract_from_path(image_path, tolerance=12, limit=num_colors)
            return [color for color, _ in colors]
        except ImportError:
            # Fallback: simple k-means clustering
            return self._extract_colors_kmeans(image_path, num_colors)
    
    def _extract_colors_kmeans(self, image_path: str, num_colors: int) -> List[Tuple[int, int, int]]:
        """Fallback color extraction using simple clustering."""
        img = Image.open(image_path).convert('RGB')
        img = img.resize((150, 150))  # Reduce size for performance
        pixels = np.array(img).reshape(-1, 3)
        
        # Simple binning instead of full k-means
        unique_colors = np.unique(pixels, axis=0)
        if len(unique_colors) <= num_colors:
            return [tuple(c) for c in unique_colors]
        
        # Sample random colors
        indices = np.random.choice(len(unique_colors), num_colors, replace=False)
        return [tuple(unique_colors[i]) for i in indices]
    
    def compare_colors(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> Dict:
        """
        Compare two colors and return detailed comparison.
        
        Returns:
            Dictionary with comparison results including distance, match status, and delta percentage
        """
        distance = color_distance(color1, color2, method="perceptual")
        max_distance = color_distance((0, 0, 0), (255, 255, 255), method="perceptual")
        delta_percentage = (distance / max_distance) * 100
        
        return {
            "color1_rgb": color1,
            "color2_rgb": color2,
            "color1_hex": rgb_to_hex(color1),
            "color2_hex": rgb_to_hex(color2),
            "distance": round(distance, 2),
            "delta_percentage": round(delta_percentage, 2),
            "is_match": distance <= self.tolerance,
            "tolerance": self.tolerance
        }
    
    def find_color_match(self, target_color: Tuple[int, int, int], 
                        color_palette: List[Tuple[int, int, int]]) -> Optional[Tuple[int, int, int]]:
        """Find closest matching color in a palette."""
        if not color_palette:
            return None
        
        distances = [color_distance(target_color, c, "perceptual") for c in color_palette]
        min_idx = np.argmin(distances)
        
        if distances[min_idx] <= self.tolerance:
            return color_palette[min_idx]
        return None
    
    def analyze_color_scheme(self, colors: List[Tuple[int, int, int]]) -> Dict:
        """Analyze a color scheme to extract metadata."""
        if not colors:
            return {}
        
        hsv_colors = [rgb_to_hsv(r/255, g/255, b/255) for r, g, b in colors]
        
        return {
            "num_colors": len(colors),
            "palette": [rgb_to_hex(c) for c in colors],
            "average_brightness": np.mean([v for _, _, v in hsv_colors]),
            "average_saturation": np.mean([s for _, s, _ in hsv_colors]),
            "has_dark_colors": any(v < 0.3 for _, _, v in hsv_colors),
            "has_bright_colors": any(v > 0.7 for _, _, v in hsv_colors),
        }
