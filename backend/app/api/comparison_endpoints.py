"""Comparison endpoints for Figma-Website comparison."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional
import uuid
import logging
from pathlib import Path
import json

from app.models.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    DiffReport,
    ProgressUpdate,
    ResponsiveComparisonRequest,
    ResponsiveReport,
    HealthCheckResponse,
    JobListResponse,
    JobListItem,
    DeleteResponse
)
from app.models.user import UserResponse
from app.services.auth import get_current_user
from app.services.job_storage import job_storage
from app.config import get_settings
from app.tasks.comparison_tasks import process_comparison_job, process_responsive_comparison
import shutil

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/compare", response_model=ComparisonResponse)
async def create_comparison(
    request: ComparisonRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[UserResponse] = Depends(get_current_user)
) -> ComparisonResponse:
    """Create a new UI comparison job."""
    job_id = str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    
    logger.info(f"Creating comparison job {job_id} for user {user_id}")
    
    job_storage.set_progress(job_id, ProgressUpdate(
        job_id=job_id,
        status="queued",
        progress=0,
        message="Job queued for processing"
    ))
    
    background_tasks.add_task(
        process_comparison_job,
        job_id,
        request.figma_input.model_dump(),
        request.website_url,
        request.options.model_dump() if request.options else {},
        user_id
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
    """Get comparison report for a job."""
    result = job_storage.get_result(job_id)
    if result:
        return result
    
    progress = job_storage.get_progress(job_id)
    if progress:
        if progress.status == "processing" or progress.status == "queued":
            raise HTTPException(
                status_code=202,
                detail=f"Job is still processing: {progress.message}"
            )
    
    report_path = Path(settings.OUTPUT_DIR) / job_id / "report.json"
    if report_path.exists():
        try:
            with open(report_path, 'r') as f:
                report_data = json.load(f)
            report = DiffReport(**report_data)
            job_storage.set_result(job_id, report)
            return report
        except Exception as e:
            logger.error(f"Failed to load report from file: {e}")
    
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/progress/{job_id}", response_model=ProgressUpdate)
async def get_progress(job_id: str) -> ProgressUpdate:
    """Get progress for a comparison job."""
    progress = job_storage.get_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return progress


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs() -> JobListResponse:
    """List all jobs."""
    jobs = {}
    for jid in job_storage.list_jobs():
        progress = job_storage.get_progress(jid)
        if progress:
            jobs[jid] = JobListItem(
                status=progress.status,
                progress=progress.progress,
                message=progress.message
            )
    return JobListResponse(jobs=jobs, storage_stats=job_storage.get_stats())


@router.delete("/job/{job_id}", response_model=DeleteResponse)
async def delete_job(job_id: str) -> DeleteResponse:
    """Delete a job and its results."""
    job_storage.delete_job(job_id)
    
    output_dir = Path(settings.OUTPUT_DIR) / job_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    return DeleteResponse(message=f"Job {job_id} deleted successfully")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        service="figma-website-diff",
        version="1.0.2"
    )


@router.post("/compare/responsive", response_model=ComparisonResponse)
async def create_responsive_comparison(
    request: ResponsiveComparisonRequest,
    background_tasks: BackgroundTasks
) -> ComparisonResponse:
    """Create a responsive UI comparison job that tests multiple viewports."""
    job_id = str(uuid.uuid4())
    
    logger.info(f"Creating responsive comparison job {job_id} with {len(request.viewports)} viewports")
    
    job_storage.set_progress(job_id, ProgressUpdate(
        job_id=job_id,
        status="queued",
        progress=0,
        message=f"Queued for processing ({len(request.viewports)} viewports)"
    ))
    
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
    """Get responsive comparison report."""
    progress = job_storage.get_progress(job_id)
    if progress and progress.status in ["processing", "queued"]:
        raise HTTPException(
            status_code=202,
            detail=f"Job is still processing: {progress.message}"
        )
    
    report_path = Path(settings.OUTPUT_DIR) / job_id / "responsive_report.json"
    if report_path.exists():
        try:
            with open(report_path, 'r') as f:
                report_data = json.load(f)
            return ResponsiveReport(**report_data)
        except Exception as e:
            logger.error(f"Failed to load responsive report: {e}")
    
    raise HTTPException(status_code=404, detail="Responsive job not found")
