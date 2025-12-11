"""PDF report generation endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import json

from app.models.schemas import DiffReport
from app.services.job_storage import job_storage
from app.services.pdf_generator import PDFReportGenerator
from app.models.database import history_db
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/report/{job_id}/pdf")
async def download_pdf_report(job_id: str) -> FileResponse:
    """Download PDF report for a completed comparison."""
    report = job_storage.get_result(job_id)
    if not report:
        report_path = Path(settings.OUTPUT_DIR) / job_id / "report.json"
        if report_path.exists():
            try:
                with open(report_path, 'r') as f:
                    report_data = json.load(f)
                report = DiffReport(**report_data)
            except Exception as e:
                logger.error(f"Failed to load report: {e}")
                raise HTTPException(status_code=404, detail="Job not found")
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report not yet completed")
    
    output_dir = Path(settings.OUTPUT_DIR) / job_id
    pdf_path = output_dir / "report.pdf"
    
    comparison_data = history_db.get_comparison(job_id)
    comparison_number = comparison_data.get('comparison_number') if comparison_data else None
    
    if not pdf_path.exists():
        pdf_generator = PDFReportGenerator()
        
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
            website_screenshot_path=website_screenshot,
            comparison_number=comparison_number
        )
    
    filename = f"ui-comparison-{comparison_number}.pdf" if comparison_number else f"ui-comparison-{job_id[:8]}.pdf"
    
    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf"
    )
