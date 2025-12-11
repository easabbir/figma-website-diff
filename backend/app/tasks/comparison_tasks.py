"""Background tasks for comparison processing."""

import logging
from pathlib import Path
from typing import Optional, List, Dict
import json

from app.models.schemas import ProgressUpdate, DiffReport
from app.services.figma_extractor import FigmaExtractor
from app.services.web_analyzer import analyze_website_async
from app.services.comparator import UIComparator
from app.services.report_generator import ReportGenerator
from app.services.job_storage import job_storage
from app.models.database import history_db, user_db
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def process_comparison_job(
    job_id: str,
    figma_input: dict,
    website_url: str,
    options: dict,
    user_id: Optional[str] = None
):
    """
    Background task to process comparison job.
    
    Args:
        job_id: Unique job identifier
        figma_input: Figma input configuration
        website_url: Website URL
        options: Comparison options
        user_id: User ID for privacy
    """
    try:
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id,
            status="processing",
            progress=10,
            message="Starting comparison...",
            current_step="initialization"
        ))
        
        output_dir = Path(settings.OUTPUT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        viewport = options.get("viewport", {"width": 1920, "height": 1080})
        history_db.save_comparison(
            job_id=job_id,
            figma_url=figma_input.get("value", ""),
            website_url=website_url,
            viewport=viewport,
            viewport_name="desktop",
            user_id=user_id
        )
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="processing", progress=20,
            message="Extracting Figma design data...", current_step="figma_extraction"
        ))
        
        figma_extractor = FigmaExtractor()
        
        if figma_input["type"] == "url":
            figma_data = figma_extractor.extract_from_url(
                figma_url=figma_input["value"],
                access_token=figma_input.get("access_token", ""),
                node_id=figma_input.get("node_id"),
                output_dir=output_dir / "figma"
            )
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Only 'url' input type is currently supported"
            )
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="processing", progress=50,
            message="Analyzing website...", current_step="website_analysis"
        ))
        
        viewport = options.get("viewport", {})
        website_data = await analyze_website_async(
            url=website_url,
            output_dir=output_dir / "website",
            viewport=viewport,
            timeout=settings.PLAYWRIGHT_TIMEOUT
        )
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="processing", progress=75,
            message="Comparing designs...", current_step="comparison"
        ))
        
        comparator = UIComparator(
            color_tolerance=options.get("tolerance", {}).get("color", settings.COLOR_TOLERANCE),
            spacing_tolerance=options.get("tolerance", {}).get("spacing", settings.SPACING_TOLERANCE),
            dimension_tolerance=options.get("tolerance", {}).get("dimension", settings.SPACING_TOLERANCE)
        )
        
        report = comparator.compare(figma_data, website_data, output_dir, job_id)
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="processing", progress=90,
            message="Generating reports...", current_step="report_generation"
        ))
        
        report_generator = ReportGenerator()
        
        json_report_path = output_dir / "report.json"
        report_generator.generate_json_report(report, json_report_path)
        
        if options.get("generate_html_report", True):
            html_report_path = output_dir / "report.html"
            comparison_data = history_db.get_comparison(job_id)
            comparison_number = comparison_data.get('comparison_number') if comparison_data else None
            report_generator.generate_html_report(report, html_report_path, comparison_number=comparison_number)
            report.report_html_url = f"/static/{job_id}/report.html"
        
        history_db.update_comparison_result(
            job_id=job_id,
            match_score=report.summary.match_score,
            total_differences=report.summary.total_differences,
            critical_count=report.summary.critical,
            warning_count=report.summary.warnings,
            info_count=report.summary.info,
            status="completed"
        )
        
        if user_id:
            new_count = user_db.increment_comparison_count(user_id)
            logger.info(f"User {user_id} comparison count: {new_count}")
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="completed", progress=100,
            message="Comparison complete!"
        ))
        
        job_storage.set_result(job_id, report)
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id,
            status="failed",
            progress=0,
            message=f"Error: {str(e)}"
        ))
        
        history_db.update_comparison_result(
            job_id=job_id,
            match_score=0,
            total_differences=0,
            critical_count=0,
            warning_count=0,
            info_count=0,
            status="failed"
        )
        
        error_report = DiffReport(
            job_id=job_id,
            status="failed",
            error=str(e)
        )
        job_storage.set_result(job_id, error_report)


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
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id,
            status="processing",
            progress=5,
            message="Starting responsive comparison...",
            current_step="initialization"
        ))
        
        output_dir = Path(settings.OUTPUT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        history_db.save_comparison(
            job_id=job_id,
            figma_url=figma_input.get("value", ""),
            website_url=website_url,
            viewport={"width": 1920, "height": 1080},
            viewport_name="responsive",
            project_name=project_name,
            tags=tags
        )
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="processing", progress=10,
            message="Extracting Figma design data..."
        ))
        
        figma_extractor = FigmaExtractor()
        figma_data = figma_extractor.extract_from_url(
            figma_url=figma_input["value"],
            access_token=figma_input.get("access_token", ""),
            node_id=figma_input.get("node_id"),
            output_dir=output_dir / "figma"
        )
        
        from app.models.schemas import ViewportResult, ResponsiveReport
        viewport_results = []
        total_viewports = len(viewports)
        
        for i, viewport in enumerate(viewports):
            viewport_name = viewport["name"]
            viewport_width = viewport["width"]
            viewport_height = viewport["height"]
            
            progress_base = 20 + (i * 70 // total_viewports)
            job_storage.set_progress(job_id, ProgressUpdate(
                job_id=job_id, status="processing", progress=progress_base,
                message=f"Analyzing {viewport_name} ({viewport_width}x{viewport_height})...",
                current_step=f"viewport_{viewport_name}"
            ))
            
            viewport_dir = output_dir / viewport_name
            viewport_dir.mkdir(parents=True, exist_ok=True)
            
            website_data = await analyze_website_async(
                url=website_url,
                output_dir=viewport_dir / "website",
                viewport={"width": viewport_width, "height": viewport_height},
                timeout=settings.PLAYWRIGHT_TIMEOUT
            )
            
            comparator = UIComparator(
                color_tolerance=options.get("tolerance", {}).get("color", settings.COLOR_TOLERANCE),
                spacing_tolerance=options.get("tolerance", {}).get("spacing", settings.SPACING_TOLERANCE),
                dimension_tolerance=options.get("tolerance", {}).get("dimension", settings.SPACING_TOLERANCE)
            )
            
            report = comparator.compare(figma_data, website_data, viewport_dir, f"{job_id}_{viewport_name}")
            
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
            
            history_db.save_viewport_result(
                comparison_id=job_id,
                viewport_name=viewport_name,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                match_score=report.summary.match_score,
                total_differences=report.summary.total_differences
            )
        
        overall_score = sum(v.match_score for v in viewport_results) / len(viewport_results) if viewport_results else 0
        total_diffs = sum(v.total_differences for v in viewport_results)
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="processing", progress=95,
            message="Generating PDF report..."
        ))
        
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
        
        history_db.update_comparison_result(
            job_id=job_id,
            match_score=overall_score,
            total_differences=total_diffs,
            critical_count=sum(v.critical for v in viewport_results),
            warning_count=sum(v.warnings for v in viewport_results),
            info_count=sum(v.info for v in viewport_results),
            status="completed"
        )
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id, status="completed", progress=100,
            message=f"Responsive comparison complete! Tested {len(viewports)} viewports."
        ))
        
        responsive_report_path = output_dir / "responsive_report.json"
        with open(responsive_report_path, 'w') as f:
            json.dump(responsive_report.model_dump(mode='json'), f, indent=2, default=str)
        
        logger.info(f"Responsive job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing responsive job {job_id}: {e}", exc_info=True)
        
        job_storage.set_progress(job_id, ProgressUpdate(
            job_id=job_id,
            status="failed",
            progress=0,
            message=str(e)
        ))
        
        history_db.update_comparison_result(
            job_id=job_id,
            match_score=0,
            total_differences=0,
            critical_count=0,
            warning_count=0,
            info_count=0,
            status="failed"
        )
