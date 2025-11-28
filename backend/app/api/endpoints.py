"""API endpoints for Figma-Website comparison."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Optional
import uuid
import logging
from pathlib import Path
import asyncio
import shutil

from ..models.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    DiffReport,
    ProgressUpdate
)
from ..services.figma_extractor import FigmaExtractor
from ..services.web_analyzer import analyze_website_async
from ..services.comparator import UIComparator
from ..services.report_generator import ReportGenerator
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
        "version": "1.0.0"
    }
