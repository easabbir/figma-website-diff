from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import datetime


class DifferenceType(str, Enum):
    """Types of differences that can be detected."""
    COLOR = "color"
    TYPOGRAPHY = "typography"
    SPACING = "spacing"
    DIMENSION = "dimension"
    LAYOUT = "layout"
    MISSING_ELEMENT = "missing_element"
    EXTRA_ELEMENT = "extra_element"
    VISUAL = "visual"


class SeverityLevel(str, Enum):
    """Severity levels for differences."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FigmaInput(BaseModel):
    """Figma design input configuration."""
    type: Literal["url", "file", "api"] = Field(..., description="Input type for Figma design")
    value: str = Field(..., description="Figma URL, file path, or file ID")
    access_token: Optional[str] = Field(None, description="Figma API access token")
    node_id: Optional[str] = Field(None, description="Specific node/frame ID to compare")


class ViewportConfig(BaseModel):
    """Viewport configuration for website capture."""
    width: int = Field(1920, ge=320, le=3840)
    height: int = Field(1080, ge=240, le=2160)


class ToleranceConfig(BaseModel):
    """Tolerance settings for comparisons."""
    color: int = Field(5, ge=0, le=100, description="Color difference tolerance (Delta E)")
    spacing: int = Field(2, ge=0, le=20, description="Spacing tolerance in pixels")
    dimension: int = Field(2, ge=0, le=20, description="Dimension tolerance in pixels")


class ComparisonOptions(BaseModel):
    """Options for comparison process."""
    viewport: ViewportConfig = Field(default_factory=ViewportConfig)
    comparison_mode: Literal["structural", "visual", "hybrid"] = Field("hybrid")
    tolerance: ToleranceConfig = Field(default_factory=ToleranceConfig)
    include_screenshots: bool = Field(True, description="Include element screenshots in report")
    generate_html_report: bool = Field(True, description="Generate HTML report")


class WebsiteInput(BaseModel):
    """Website input configuration."""
    url: HttpUrl = Field(..., description="Website URL to compare")
    wait_for_selector: Optional[str] = Field(None, description="CSS selector to wait for before capture")
    wait_timeout: Optional[int] = Field(5000, description="Wait timeout in milliseconds")


class ComparisonRequest(BaseModel):
    """Request model for comparison API."""
    figma_input: FigmaInput
    website_url: str
    options: Optional[ComparisonOptions] = Field(default_factory=ComparisonOptions)


class Difference(BaseModel):
    """Individual difference found during comparison."""
    id: str = Field(..., description="Unique identifier for this difference")
    type: DifferenceType
    severity: SeverityLevel
    element_selector: Optional[str] = Field(None, description="CSS selector for the element")
    element_name: Optional[str] = Field(None, description="Element name or description")
    figma_value: Any = Field(None, description="Value from Figma design")
    website_value: Any = Field(None, description="Value from website")
    delta: Optional[str] = Field(None, description="Calculated difference/delta")
    description: str = Field(..., description="Human-readable description of the difference")
    screenshot_url: Optional[str] = Field(None, description="URL to difference screenshot")
    coordinates: Optional[Dict[str, int]] = Field(None, description="Element coordinates")


class ComparisonSummary(BaseModel):
    """Summary statistics for comparison results."""
    total_differences: int = 0
    critical: int = 0
    warnings: int = 0
    info: int = 0
    match_score: float = Field(0.0, ge=0.0, le=100.0, description="Overall match percentage")


class DiffReport(BaseModel):
    """Complete difference report."""
    job_id: str
    status: Literal["processing", "completed", "failed"] = "processing"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    summary: ComparisonSummary = Field(default_factory=ComparisonSummary)
    differences: List[Difference] = Field(default_factory=list)
    figma_screenshot_url: Optional[str] = None
    website_screenshot_url: Optional[str] = None
    visual_diff_url: Optional[str] = None
    report_html_url: Optional[str] = None
    error: Optional[str] = None


class ComparisonResponse(BaseModel):
    """Response model for comparison API."""
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    message: str
    progress_url: Optional[str] = None
    report_url: Optional[str] = None


class ProgressUpdate(BaseModel):
    """WebSocket progress update."""
    job_id: str
    status: str
    progress: int = Field(0, ge=0, le=100)
    message: str
    current_step: Optional[str] = None
