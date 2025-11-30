"""API endpoints for Figma-Website comparison."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Optional, List
import uuid
import logging
from pathlib import Path
import asyncio
import shutil
import json

from ..models.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    DiffReport,
    ProgressUpdate,
    ResponsiveComparisonRequest,
    ResponsiveReport,
    ViewportResult,
    HistoryItem,
    HistoryResponse,
    HistoryStats,
    SeverityLevel
)
from ..services.figma_extractor import FigmaExtractor
from ..services.web_analyzer import analyze_website_async
from ..services.comparator import UIComparator
from ..services.report_generator import ReportGenerator
from ..services.pdf_generator import PDFReportGenerator
from ..models.database import history_db
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# In-memory storage for job results (use Redis in production)
job_results: Dict[str, DiffReport] = {}
job_progress: Dict[str, ProgressUpdate] = {}


async def process_comparison_job(
    job_id: str,
    figma_input: dict,
    website_url: str,
    options: dict
):
    """
    Background task to process comparison job.
    
    Args:
        job_id: Unique job identifier
        figma_input: Figma input configuration
        website_url: Website URL
        options: Comparison options
    """
    try:
        # Update progress
        job_progress[job_id] = ProgressUpdate(
            job_id=job_id,
            status="processing",
            progress=10,
            message="Starting comparison...",
            current_step="initialization"
        )
        
        # Create output directory
        output_dir = Path(settings.OUTPUT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Extract Figma data
        job_progress[job_id].progress = 20
        job_progress[job_id].message = "Extracting Figma design data..."
        job_progress[job_id].current_step = "figma_extraction"
        
        figma_extractor = FigmaExtractor()
        
        if figma_input["type"] == "url":
            figma_data = figma_extractor.extract_from_url(
                figma_url=figma_input["value"],
                access_token=figma_input.get("access_token", ""),
                node_id=figma_input.get("node_id"),
                output_dir=output_dir / "figma"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Only 'url' input type is currently supported"
            )
        
        # Step 2: Analyze website
        job_progress[job_id].progress = 50
        job_progress[job_id].message = "Analyzing website..."
        job_progress[job_id].current_step = "website_analysis"
        
        viewport = options.get("viewport", {})
        website_data = await analyze_website_async(
            url=website_url,
            output_dir=output_dir / "website",
            viewport=viewport,
            timeout=settings.PLAYWRIGHT_TIMEOUT
        )
        
        # Step 3: Compare
        job_progress[job_id].progress = 75
        job_progress[job_id].message = "Comparing designs..."
        job_progress[job_id].current_step = "comparison"
        
        comparator = UIComparator(
            color_tolerance=options.get("tolerance", {}).get("color", settings.COLOR_TOLERANCE),
            spacing_tolerance=options.get("tolerance", {}).get("spacing", settings.SPACING_TOLERANCE),
            dimension_tolerance=options.get("tolerance", {}).get("dimension", settings.SPACING_TOLERANCE)
        )
        
        report = comparator.compare(figma_data, website_data, output_dir, job_id)
        
        # Step 4: Generate reports
        job_progress[job_id].progress = 90
        job_progress[job_id].message = "Generating reports..."
        job_progress[job_id].current_step = "report_generation"
        
        report_generator = ReportGenerator()
        
        # Generate JSON report
        json_report_path = output_dir / "report.json"
        report_generator.generate_json_report(report, json_report_path)
        
        # Generate HTML report
        if options.get("generate_html_report", True):
            html_report_path = output_dir / "report.html"
            report_generator.generate_html_report(report, html_report_path)
            report.report_html_url = f"/static/{job_id}/report.html"
        
        # Complete
        job_progress[job_id].progress = 100
        job_progress[job_id].status = "completed"
        job_progress[job_id].message = "Comparison complete!"
        
        job_results[job_id] = report
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        
        job_progress[job_id] = ProgressUpdate(
            job_id=job_id,
            status="failed",
            progress=0,
            message=f"Error: {str(e)}"
        )
        
        # Create error report
        error_report = DiffReport(
            job_id=job_id,
            status="failed",
            error=str(e)
        )
        job_results[job_id] = error_report


@router.post("/compare", response_model=ComparisonResponse)
async def create_comparison(
    request: ComparisonRequest,
    background_tasks: BackgroundTasks
) -> ComparisonResponse:
    """
    Create a new UI comparison job.
    
    Args:
        request: Comparison request with Figma and website details
        background_tasks: FastAPI background tasks
        
    Returns:
        Response with job ID and status
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    logger.info(f"Creating comparison job {job_id}")
    
    # Initialize progress
    job_progress[job_id] = ProgressUpdate(
        job_id=job_id,
        status="queued",
        progress=0,
        message="Job queued for processing"
    )
    
    # Add background task
    background_tasks.add_task(
        process_comparison_job,
        job_id,
        request.figma_input.model_dump(),
        request.website_url,
        request.options.model_dump() if request.options else {}
    )
    
    return ComparisonResponse(
        job_id=job_id,
        status="queued",
        message="Comparison job created successfully",
        progress_url=f"/api/v1/progress/{job_id}",
        report_url=f"/api/v1/report/{job_id}"
    )


@router.get("/report/{job_id}", response_model=DiffReport)
async def get_report(job_id: str) -> DiffReport:
    """
    Get comparison report for a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Difference report
    """
    if job_id not in job_results:
        # Check if job is in progress
        if job_id in job_progress:
            progress = job_progress[job_id]
            if progress.status == "processing" or progress.status == "queued":
                raise HTTPException(
                    status_code=202,
                    detail=f"Job is still processing: {progress.message}"
                )
        
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_results[job_id]


@router.get("/progress/{job_id}", response_model=ProgressUpdate)
async def get_progress(job_id: str) -> ProgressUpdate:
    """
    Get progress for a comparison job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Progress update
    """
    if job_id not in job_progress:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_progress[job_id]


@router.get("/jobs")
async def list_jobs() -> Dict:
    """
    List all jobs.
    
    Returns:
        Dictionary of job IDs and their status
    """
    jobs = {}
    for job_id in job_progress.keys():
        jobs[job_id] = {
            "status": job_progress[job_id].status,
            "progress": job_progress[job_id].progress,
            "message": job_progress[job_id].message
        }
    return {"jobs": jobs}


@router.delete("/job/{job_id}")
async def delete_job(job_id: str) -> Dict:
    """
    Delete a job and its results.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Confirmation message
    """
    # Remove from memory
    job_results.pop(job_id, None)
    job_progress.pop(job_id, None)
    
    # Remove files
    output_dir = Path(settings.OUTPUT_DIR) / job_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    return {"message": f"Job {job_id} deleted successfully"}


@router.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "figma-website-diff",
        "version": "1.0.2"
    }


# ============ PDF Export Endpoints ============

@router.get("/report/{job_id}/pdf")
async def download_pdf_report(job_id: str) -> FileResponse:
    """
    Download PDF report for a completed comparison.
    
    Args:
        job_id: Job identifier
        
    Returns:
        PDF file download
    """
    if job_id not in job_results:
        raise HTTPException(status_code=404, detail="Job not found")
    
    report = job_results[job_id]
    
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report not yet completed")
    
    # Generate PDF
    output_dir = Path(settings.OUTPUT_DIR) / job_id
    pdf_path = output_dir / "report.pdf"
    
    if not pdf_path.exists():
        # Generate PDF on demand
        pdf_generator = PDFReportGenerator()
        
        # Get screenshot paths
        figma_screenshot = None
        website_screenshot = None
        
        if report.figma_screenshot_url:
            figma_screenshot = str(output_dir / "figma" / Path(report.figma_screenshot_url).name)
        if report.website_screenshot_url:
            website_screenshot = str(output_dir / "website" / "website_screenshot.png")
        
        pdf_generator.generate_pdf_report(
            report,
            pdf_path,
            figma_screenshot_path=figma_screenshot,
            website_screenshot_path=website_screenshot
        )
    
    return FileResponse(
        path=str(pdf_path),
        filename=f"ui-comparison-{job_id[:8]}.pdf",
        media_type="application/pdf"
    )


# ============ History Endpoints ============

@router.get("/history", response_model=HistoryResponse)
async def get_comparison_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    website_url: Optional[str] = None,
    project_name: Optional[str] = None,
    status: Optional[str] = None
) -> HistoryResponse:
    """
    Get comparison history with optional filters.
    
    Args:
        limit: Maximum number of results
        offset: Offset for pagination
        website_url: Filter by website URL
        project_name: Filter by project name
        status: Filter by status
        
    Returns:
        List of historical comparisons
    """
    items = history_db.get_history(
        limit=limit,
        offset=offset,
        website_url=website_url,
        project_name=project_name,
        status=status
    )
    
    history_items = []
    for item in items:
        history_items.append(HistoryItem(
            id=item["id"],
            job_id=item["job_id"],
            figma_url=item.get("figma_url"),
            website_url=item["website_url"],
            viewport_name=item.get("viewport_name", "desktop"),
            viewport_width=item.get("viewport_width", 1920),
            viewport_height=item.get("viewport_height", 1080),
            match_score=item.get("match_score", 0.0),
            total_differences=item.get("total_differences", 0),
            critical_count=item.get("critical_count", 0),
            warning_count=item.get("warning_count", 0),
            info_count=item.get("info_count", 0),
            status=item.get("status", "pending"),
            project_name=item.get("project_name"),
            tags=json.loads(item["tags"]) if item.get("tags") else None,
            created_at=item["created_at"],
            completed_at=item.get("completed_at")
        ))
    
    return HistoryResponse(
        items=history_items,
        total=len(history_items),
        page=(offset // limit) + 1,
        limit=limit
    )


@router.get("/history/stats", response_model=HistoryStats)
async def get_history_stats() -> HistoryStats:
    """Get overall statistics for comparison history."""
    stats = history_db.get_stats()
    return HistoryStats(
        total_comparisons=stats.get("total_comparisons", 0) or 0,
        avg_match_score=stats.get("avg_match_score", 0.0) or 0.0,
        total_differences_found=stats.get("total_differences_found", 0) or 0,
        unique_websites=stats.get("unique_websites", 0) or 0
    )


@router.delete("/history/{job_id}")
async def delete_history_item(job_id: str) -> Dict:
    """Delete a comparison from history."""
    deleted = history_db.delete_comparison(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History item not found")
    return {"message": f"History item {job_id} deleted successfully"}


# ============ Responsive Mode Endpoints ============

responsive_job_results: Dict[str, ResponsiveReport] = {}


async def process_responsive_comparison(
    job_id: str,
    figma_input: dict,
    website_url: str,
    viewports: List[dict],
    options: dict,
    project_name: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """
    Background task to process responsive comparison across multiple viewports.
    """
    try:
        # Initialize progress
        job_progress[job_id] = ProgressUpdate(
            job_id=job_id,
            status="processing",
            progress=5,
            message="Starting responsive comparison...",
            current_step="initialization"
        )
        
        # Create output directory
        output_dir = Path(settings.OUTPUT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to history
        history_db.save_comparison(
            job_id=job_id,
            figma_url=figma_input.get("value", ""),
            website_url=website_url,
            viewport={"width": 1920, "height": 1080},
            viewport_name="responsive",
            project_name=project_name,
            tags=tags
        )
        
        # Extract Figma data once (reuse for all viewports)
        job_progress[job_id].progress = 10
        job_progress[job_id].message = "Extracting Figma design data..."
        
        figma_extractor = FigmaExtractor()
        figma_data = figma_extractor.extract_from_url(
            figma_url=figma_input["value"],
            access_token=figma_input.get("access_token", ""),
            node_id=figma_input.get("node_id"),
            output_dir=output_dir / "figma"
        )
        
        # Process each viewport
        viewport_results = []
        total_viewports = len(viewports)
        
        for i, viewport in enumerate(viewports):
            viewport_name = viewport["name"]
            viewport_width = viewport["width"]
            viewport_height = viewport["height"]
            
            progress_base = 20 + (i * 70 // total_viewports)
            job_progress[job_id].progress = progress_base
            job_progress[job_id].message = f"Analyzing {viewport_name} ({viewport_width}x{viewport_height})..."
            job_progress[job_id].current_step = f"viewport_{viewport_name}"
            
            # Create viewport-specific output directory
            viewport_dir = output_dir / viewport_name
            viewport_dir.mkdir(parents=True, exist_ok=True)
            
            # Analyze website at this viewport
            website_data = await analyze_website_async(
                url=website_url,
                output_dir=viewport_dir / "website",
                viewport={"width": viewport_width, "height": viewport_height},
                timeout=settings.PLAYWRIGHT_TIMEOUT
            )
            
            # Compare
            comparator = UIComparator(
                color_tolerance=options.get("tolerance", {}).get("color", settings.COLOR_TOLERANCE),
                spacing_tolerance=options.get("tolerance", {}).get("spacing", settings.SPACING_TOLERANCE),
                dimension_tolerance=options.get("tolerance", {}).get("dimension", settings.SPACING_TOLERANCE)
            )
            
            report = comparator.compare(figma_data, website_data, viewport_dir, f"{job_id}_{viewport_name}")
            
            # Create viewport result
            viewport_result = ViewportResult(
                viewport_name=viewport_name,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                match_score=report.summary.match_score,
                total_differences=report.summary.total_differences,
                critical=report.summary.critical,
                warnings=report.summary.warnings,
                info=report.summary.info,
                figma_screenshot_url=f"/static/{job_id}/{viewport_name}/figma/screenshot.png",
                website_screenshot_url=f"/static/{job_id}/{viewport_name}/website/website_screenshot.png",
                visual_diff_url=f"/static/{job_id}/{viewport_name}/visual_diff.png" if report.visual_diff_url else None,
                differences=report.differences
            )
            viewport_results.append(viewport_result)
            
            # Save to database
            history_db.save_viewport_result(
                comparison_id=job_id,
                viewport_name=viewport_name,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                match_score=report.summary.match_score,
                total_differences=report.summary.total_differences
            )
        
        # Calculate overall score
        overall_score = sum(v.match_score for v in viewport_results) / len(viewport_results) if viewport_results else 0
        total_diffs = sum(v.total_differences for v in viewport_results)
        
        # Generate PDF report
        job_progress[job_id].progress = 95
        job_progress[job_id].message = "Generating PDF report..."
        
        # Create responsive report
        responsive_report = ResponsiveReport(
            job_id=job_id,
            status="completed",
            figma_url=figma_input.get("value"),
            website_url=website_url,
            project_name=project_name,
            viewport_results=viewport_results,
            overall_match_score=overall_score,
            total_differences=total_diffs,
            report_pdf_url=f"/api/v1/report/{job_id}/responsive-pdf"
        )
        
        # Update history
        history_db.update_comparison_result(
            job_id=job_id,
            match_score=overall_score,
            total_differences=total_diffs,
            critical_count=sum(v.critical for v in viewport_results),
            warning_count=sum(v.warnings for v in viewport_results),
            info_count=sum(v.info for v in viewport_results),
            status="completed"
        )
        
        # Complete
        job_progress[job_id].progress = 100
        job_progress[job_id].status = "completed"
        job_progress[job_id].message = f"Responsive comparison complete! Tested {len(viewports)} viewports."
        
        responsive_job_results[job_id] = responsive_report
        
        logger.info(f"Responsive job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing responsive job {job_id}: {e}", exc_info=True)
        
        job_progress[job_id] = ProgressUpdate(
            job_id=job_id,
            status="failed",
            progress=0,
            message=str(e)
        )
        
        history_db.update_comparison_result(
            job_id=job_id,
            match_score=0,
            total_differences=0,
            critical_count=0,
            warning_count=0,
            info_count=0,
            status="failed"
        )


@router.post("/compare/responsive", response_model=ComparisonResponse)
async def create_responsive_comparison(
    request: ResponsiveComparisonRequest,
    background_tasks: BackgroundTasks
) -> ComparisonResponse:
    """
    Create a responsive UI comparison job that tests multiple viewports.
    
    Args:
        request: Responsive comparison request with viewports
        background_tasks: FastAPI background tasks
        
    Returns:
        Response with job ID and status
    """
    job_id = str(uuid.uuid4())
    
    logger.info(f"Creating responsive comparison job {job_id} with {len(request.viewports)} viewports")
    
    # Initialize progress
    job_progress[job_id] = ProgressUpdate(
        job_id=job_id,
        status="queued",
        progress=0,
        message=f"Queued for processing ({len(request.viewports)} viewports)"
    )
    
    # Add background task
    background_tasks.add_task(
        process_responsive_comparison,
        job_id,
        request.figma_input.model_dump(),
        request.website_url,
        [v.model_dump() for v in request.viewports],
        request.options.model_dump() if request.options else {},
        request.project_name,
        request.tags
    )
    
    return ComparisonResponse(
        job_id=job_id,
        status="queued",
        message=f"Responsive comparison job created with {len(request.viewports)} viewports",
        progress_url=f"/api/v1/progress/{job_id}",
        report_url=f"/api/v1/report/{job_id}/responsive"
    )


@router.get("/report/{job_id}/responsive", response_model=ResponsiveReport)
async def get_responsive_report(job_id: str) -> ResponsiveReport:
    """
    Get responsive comparison report.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Responsive comparison report with all viewport results
    """
    if job_id not in responsive_job_results:
        if job_id in job_progress:
            progress = job_progress[job_id]
            if progress.status in ["processing", "queued"]:
                raise HTTPException(
                    status_code=202,
                    detail=f"Job is still processing: {progress.message}"
                )
        raise HTTPException(status_code=404, detail="Responsive job not found")
    
    return responsive_job_results[job_id]
