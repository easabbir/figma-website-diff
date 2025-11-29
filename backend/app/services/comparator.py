"""UI comparison engine for Figma vs Website."""

from typing import Dict, List, Optional, Tuple
import uuid
import logging
from pathlib import Path

from ..models.schemas import (
    Difference, DifferenceType, SeverityLevel,
    ComparisonSummary, DiffReport
)
from ..utils.color_utils import ColorAnalyzer, parse_css_color, hex_to_rgb
from ..utils.layout_utils import LayoutAnalyzer, compare_dimensions, calculate_spacing
from ..utils.image_utils import create_visual_diff, calculate_similarity

logger = logging.getLogger(__name__)


class UIComparator:
    """Compare Figma designs with website implementations."""
    
    def __init__(self, color_tolerance: int = 5, 
                 spacing_tolerance: int = 2,
                 dimension_tolerance: int = 2):
        """
        Initialize UI comparator.
        
        Args:
            color_tolerance: Color difference tolerance
            spacing_tolerance: Spacing difference tolerance in pixels
            dimension_tolerance: Dimension difference tolerance in pixels
        """
        self.color_analyzer = ColorAnalyzer(tolerance=color_tolerance)
        self.layout_analyzer = LayoutAnalyzer(
            spacing_tolerance=spacing_tolerance,
            dimension_tolerance=dimension_tolerance
        )
        self.color_tolerance = color_tolerance
        self.spacing_tolerance = spacing_tolerance
        self.dimension_tolerance = dimension_tolerance
    
    def compare(self, figma_data: Dict, website_data: Dict, 
               output_dir: Path, job_id: str) -> DiffReport:
        """
        Perform complete UI comparison.
        
        Args:
            figma_data: Extracted Figma design data
            website_data: Analyzed website data
            output_dir: Directory for output files
            job_id: Unique job identifier
            
        Returns:
            Complete difference report
        """
        logger.info(f"Starting UI comparison for job {job_id}")
        
        differences = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Compare colors
        logger.info("Comparing colors...")
        color_diffs = self._compare_colors(figma_data, website_data)
        differences.extend(color_diffs)
        
        # Compare typography
        logger.info("Comparing typography...")
        typography_diffs = self._compare_typography(figma_data, website_data)
        differences.extend(typography_diffs)
        
        # Compare layout and spacing
        logger.info("Comparing layout...")
        layout_diffs = self._compare_layout(figma_data, website_data)
        differences.extend(layout_diffs)
        
        # Compare dimensions
        logger.info("Comparing dimensions...")
        dimension_diffs = self._compare_dimensions(figma_data, website_data)
        differences.extend(dimension_diffs)
        
        # Visual comparison (if screenshots available)
        visual_diff_url = None
        similarity_scores = {}
        
        figma_screenshot = figma_data.get("image_exports", {})
        website_screenshot = website_data.get("screenshot")
        
        if figma_screenshot and website_screenshot:
            logger.info("Performing visual comparison...")
            
            # Get first Figma screenshot (assume single frame comparison)
            figma_img = list(figma_screenshot.values())[0] if isinstance(figma_screenshot, dict) else figma_screenshot
            
            try:
                # Create visual diff
                visual_diff_path = output_dir / "visual_diff.png"
                create_visual_diff(
                    figma_img,
                    website_screenshot,
                    str(visual_diff_path),
                    mode="side-by-side"
                )
                visual_diff_url = f"/static/{job_id}/visual_diff.png"
                
                # Calculate similarity
                similarity_scores = calculate_similarity(figma_img, website_screenshot)
                
                # Add visual difference if similarity is low
                if similarity_scores.get("overall", 100) < 90:
                    visual_diffs = self._create_visual_differences(similarity_scores)
                    differences.extend(visual_diffs)
                    
            except Exception as e:
                logger.error(f"Error in visual comparison: {e}")
        
        # Calculate summary
        summary = self._calculate_summary(differences, similarity_scores)
        
        # Determine screenshot URLs
        figma_screenshot_url = None
        website_screenshot_url = None
        
        if figma_screenshot:
            # Get the first Figma screenshot path
            if isinstance(figma_screenshot, dict):
                first_img = list(figma_screenshot.values())[0]
                # Extract relative path from full path
                img_path = Path(first_img)
                figma_screenshot_url = f"/static/{job_id}/figma/{img_path.name}"
            else:
                figma_screenshot_url = f"/static/{job_id}/figma/screenshot.png"
        
        if website_screenshot:
            # Website screenshot is typically at website/website_screenshot.png
            website_screenshot_url = f"/static/{job_id}/website/website_screenshot.png"
        
        # Create report
        report = DiffReport(
            job_id=job_id,
            status="completed",
            summary=summary,
            differences=differences,
            figma_screenshot_url=figma_screenshot_url,
            website_screenshot_url=website_screenshot_url,
            visual_diff_url=visual_diff_url
        )
        
        logger.info(f"Comparison complete. Found {summary.total_differences} differences.")
        
        return report
    
    def _compare_colors(self, figma_data: Dict, website_data: Dict) -> List[Difference]:
        """Compare color usage between Figma and website."""
        differences = []
        
        # Extract Figma colors from design tokens
        figma_colors = set()
        for token in figma_data.get("design_tokens", []):
            for fill in token.get("fills", []):
                if fill.get("type") == "SOLID" and fill.get("color"):
                    figma_colors.add(fill["color"].lower())
        
        # Extract website colors
        website_colors = set(c.lower() for c in website_data.get("colors", []))
        
        # Find missing colors (in Figma but not on website)
        for figma_color in figma_colors:
            try:
                figma_rgb = hex_to_rgb(figma_color)
                
                # Try to find matching color in website
                matched = False
                closest_color = None
                min_distance = float('inf')
                
                for web_color in website_colors:
                    try:
                        web_rgb = hex_to_rgb(web_color)
                        comparison = self.color_analyzer.compare_colors(figma_rgb, web_rgb)
                        
                        if comparison["is_match"]:
                            matched = True
                            break
                        
                        if comparison["distance"] < min_distance:
                            min_distance = comparison["distance"]
                            closest_color = web_color
                            
                    except:
                        continue
                
                if not matched and closest_color:
                    # Color mismatch found
                    web_rgb = hex_to_rgb(closest_color)
                    comparison = self.color_analyzer.compare_colors(figma_rgb, web_rgb)
                    
                    differences.append(Difference(
                        id=str(uuid.uuid4()),
                        type=DifferenceType.COLOR,
                        severity=SeverityLevel.WARNING if comparison["delta_percentage"] < 10 else SeverityLevel.CRITICAL,
                        figma_value=figma_color,
                        website_value=closest_color,
                        delta=f"{comparison['delta_percentage']:.1f}% difference",
                        description=f"Color mismatch: Figma {figma_color} vs Website {closest_color}"
                    ))
                    
            except Exception as e:
                logger.debug(f"Error comparing color {figma_color}: {e}")
                continue
        
        return differences
    
    def _compare_typography(self, figma_data: Dict, website_data: Dict) -> List[Difference]:
        """Compare typography between Figma and website."""
        differences = []
        
        # Extract Figma typography
        figma_fonts = {}
        for token in figma_data.get("design_tokens", []):
            typography = token.get("typography")
            if typography and typography.get("font_family"):
                key = typography["font_family"]
                if key not in figma_fonts:
                    figma_fonts[key] = typography
        
        # Extract website fonts
        website_fonts = {
            f["family"]: f
            for f in website_data.get("fonts", [])
        }
        
        # Compare font families
        figma_families = set(figma_fonts.keys())
        website_families = set(website_fonts.keys())
        
        missing_fonts = figma_families - website_families
        for font in missing_fonts:
            differences.append(Difference(
                id=str(uuid.uuid4()),
                type=DifferenceType.TYPOGRAPHY,
                severity=SeverityLevel.CRITICAL,
                figma_value=font,
                website_value=None,
                description=f"Font family '{font}' from Figma not found on website"
            ))
        
        # Compare font sizes and weights for common fonts
        for font_family in figma_families.intersection(website_families):
            figma_font = figma_fonts[font_family]
            # Note: Website fonts might have multiple sizes, just flag if family exists
            # More detailed comparison would require element-by-element matching
        
        return differences
    
    def _compare_layout(self, figma_data: Dict, website_data: Dict) -> List[Difference]:
        """Compare layout and spacing."""
        differences = []
        
        # Extract layout elements from Figma
        figma_elements = []
        for token in figma_data.get("design_tokens", []):
            bounds = token.get("bounds")
            layout = token.get("layout")
            if bounds and layout:
                figma_elements.append({
                    "name": token.get("name"),
                    "bounds": bounds,
                    "layout": layout
                })
        
        # Compare spacing consistency
        if len(figma_elements) >= 3:
            figma_spacing = self.layout_analyzer.calculate_spacing_consistency(
                [e["bounds"] for e in figma_elements]
            )
            
            # This is simplified - in a full implementation, you'd match elements
            # between Figma and website and compare their spacing
            if not figma_spacing.get("consistent"):
                differences.append(Difference(
                    id=str(uuid.uuid4()),
                    type=DifferenceType.SPACING,
                    severity=SeverityLevel.INFO,
                    description="Spacing inconsistency detected in design"
                ))
        
        return differences
    
    def _compare_dimensions(self, figma_data: Dict, website_data: Dict) -> List[Difference]:
        """Compare element dimensions."""
        differences = []
        
        # This is a simplified version
        # Full implementation would require element matching between Figma and website
        
        # Compare overall viewport/frame sizes
        figma_tokens = figma_data.get("design_tokens", [])
        if figma_tokens:
            # Get root frame dimensions
            root_token = figma_tokens[0]  # Assume first is root
            figma_bounds = root_token.get("bounds", {})
            
            website_viewport = website_data.get("viewport", {})
            
            if figma_bounds and website_viewport:
                width_diff = abs(figma_bounds.get("width", 0) - website_viewport.get("width", 0))
                height_diff = abs(figma_bounds.get("height", 0) - website_viewport.get("height", 0))
                
                if width_diff > self.dimension_tolerance:
                    differences.append(Difference(
                        id=str(uuid.uuid4()),
                        type=DifferenceType.DIMENSION,
                        severity=SeverityLevel.WARNING,
                        figma_value=f"{figma_bounds.get('width')}px",
                        website_value=f"{website_viewport.get('width')}px",
                        delta=f"{width_diff}px difference",
                        description=f"Width mismatch: Figma frame vs website viewport"
                    ))
        
        return differences
    
    def _create_visual_differences(self, similarity_scores: Dict) -> List[Difference]:
        """Create visual difference entries based on similarity scores."""
        differences = []
        
        overall_score = similarity_scores.get("overall", 100)
        
        if overall_score < 90:
            severity = SeverityLevel.CRITICAL if overall_score < 70 else SeverityLevel.WARNING
            
            differences.append(Difference(
                id=str(uuid.uuid4()),
                type=DifferenceType.VISUAL,
                severity=severity,
                figma_value=f"{overall_score:.1f}% match",
                website_value="Visual rendering",
                delta=f"{100 - overall_score:.1f}% difference",
                description=f"Visual similarity: {overall_score:.1f}% (SSIM: {similarity_scores.get('ssim', 0):.1f}%)"
            ))
        
        return differences
    
    def _calculate_summary(self, differences: List[Difference], 
                          similarity_scores: Dict) -> ComparisonSummary:
        """Calculate summary statistics."""
        summary = ComparisonSummary(
            total_differences=len(differences),
            critical=sum(1 for d in differences if d.severity == SeverityLevel.CRITICAL),
            warnings=sum(1 for d in differences if d.severity == SeverityLevel.WARNING),
            info=sum(1 for d in differences if d.severity == SeverityLevel.INFO)
        )
        
        # Calculate overall match score
        if similarity_scores and similarity_scores.get("overall"):
            visual_score = similarity_scores.get("overall", 100)
        else:
            # If no visual comparison was done, base score on differences only
            visual_score = 100
        
        logger.info(f"Visual score: {visual_score}, Similarity scores: {similarity_scores}")
        
        # Calculate match score based on visual similarity and differences
        # Visual similarity contributes 60%, structural differences contribute 40%
        visual_component = visual_score * 0.6
        
        # Structural component: penalize based on differences
        # Critical: -3 points, Warning: -1.5 points, Info: -0.5 points
        critical_count = sum(1 for d in differences if d.severity == SeverityLevel.CRITICAL)
        warning_count = sum(1 for d in differences if d.severity == SeverityLevel.WARNING)
        info_count = sum(1 for d in differences if d.severity == SeverityLevel.INFO)
        
        structural_penalty = (critical_count * 3) + (warning_count * 1.5) + (info_count * 0.5)
        structural_component = max(0, 40 - structural_penalty)
        
        summary.match_score = round(max(0, min(100, visual_component + structural_component)), 1)
        
        logger.info(f"Match score calculation: visual={visual_component:.1f}, structural={structural_component:.1f}, total={summary.match_score:.1f}")
        
        return summary
