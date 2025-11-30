"""PDF Report Generator for UI Comparison Reports."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging
import os

from ..models.schemas import DiffReport, SeverityLevel

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """Generate professional PDF reports for UI comparisons."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a1a2e')
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666')
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#4a4a6a')
        ))
        
        # Score style
        self.styles.add(ParagraphStyle(
            name='ScoreStyle',
            parent=self.styles['Normal'],
            fontSize=48,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#10b981')
        ))
        
        # Critical style
        self.styles.add(ParagraphStyle(
            name='Critical',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#dc2626')
        ))
        
        # Warning style
        self.styles.add(ParagraphStyle(
            name='Warning',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#f59e0b')
        ))
        
        # Info style
        self.styles.add(ParagraphStyle(
            name='Info',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#3b82f6')
        ))
    
    def generate_pdf_report(self, report: DiffReport, output_path: Path,
                           figma_screenshot_path: Optional[str] = None,
                           website_screenshot_path: Optional[str] = None) -> str:
        """
        Generate a PDF report from comparison results.
        
        Args:
            report: The comparison report data
            output_path: Path to save the PDF
            figma_screenshot_path: Path to Figma screenshot
            website_screenshot_path: Path to website screenshot
            
        Returns:
            Path to generated PDF
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Title
        story.append(Paragraph("UI Comparison Report", self.styles['ReportTitle']))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['ReportSubtitle']
        ))
        story.append(Paragraph(f"Job ID: {report.job_id}", self.styles['ReportSubtitle']))
        
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        if report.summary:
            # Match Score
            score_color = self._get_score_color(report.summary.match_score)
            story.append(Paragraph(
                f"<font color='{score_color}'>{report.summary.match_score:.1f}%</font>",
                self.styles['ScoreStyle']
            ))
            story.append(Paragraph("Overall Match Score", self.styles['ReportSubtitle']))
            story.append(Spacer(1, 20))
            
            # Summary table
            summary_data = [
                ['Metric', 'Count'],
                ['Total Differences', str(report.summary.total_differences)],
                ['Critical Issues', str(report.summary.critical)],
                ['Warnings', str(report.summary.warnings)],
                ['Info', str(report.summary.info)],
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a6a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9fafb')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            story.append(summary_table)
        
        story.append(Spacer(1, 30))
        
        # Screenshots Section
        if figma_screenshot_path or website_screenshot_path:
            story.append(Paragraph("Visual Comparison", self.styles['SectionHeader']))
            story.append(Spacer(1, 10))
            
            screenshot_data = []
            headers = []
            images = []
            
            if figma_screenshot_path and os.path.exists(figma_screenshot_path):
                headers.append('Figma Design')
                try:
                    img = Image(figma_screenshot_path, width=2.5*inch, height=2*inch)
                    img.hAlign = 'CENTER'
                    images.append(img)
                except Exception as e:
                    logger.warning(f"Could not load Figma screenshot: {e}")
                    images.append(Paragraph("Image not available", self.styles['Normal']))
            
            if website_screenshot_path and os.path.exists(website_screenshot_path):
                headers.append('Website')
                try:
                    img = Image(website_screenshot_path, width=2.5*inch, height=2*inch)
                    img.hAlign = 'CENTER'
                    images.append(img)
                except Exception as e:
                    logger.warning(f"Could not load website screenshot: {e}")
                    images.append(Paragraph("Image not available", self.styles['Normal']))
            
            if images:
                screenshot_table = Table([headers, images], colWidths=[2.8*inch] * len(images))
                screenshot_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('TOPPADDING', (0, 1), (-1, 1), 10),
                ]))
                story.append(screenshot_table)
        
        story.append(PageBreak())
        
        # Differences Section
        story.append(Paragraph("Detailed Differences", self.styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        if report.differences:
            # Group by severity
            critical_diffs = [d for d in report.differences if d.severity == SeverityLevel.CRITICAL]
            warning_diffs = [d for d in report.differences if d.severity == SeverityLevel.WARNING]
            info_diffs = [d for d in report.differences if d.severity == SeverityLevel.INFO]
            
            # Critical Issues
            if critical_diffs:
                story.append(Paragraph(
                    f"<font color='#dc2626'>● Critical Issues ({len(critical_diffs)})</font>",
                    self.styles['Heading3']
                ))
                story.append(Spacer(1, 5))
                
                for diff in critical_diffs[:10]:  # Limit to 10
                    story.append(self._create_difference_entry(diff, 'Critical'))
                
                if len(critical_diffs) > 10:
                    story.append(Paragraph(
                        f"... and {len(critical_diffs) - 10} more critical issues",
                        self.styles['Normal']
                    ))
                story.append(Spacer(1, 15))
            
            # Warnings
            if warning_diffs:
                story.append(Paragraph(
                    f"<font color='#f59e0b'>● Warnings ({len(warning_diffs)})</font>",
                    self.styles['Heading3']
                ))
                story.append(Spacer(1, 5))
                
                for diff in warning_diffs[:10]:
                    story.append(self._create_difference_entry(diff, 'Warning'))
                
                if len(warning_diffs) > 10:
                    story.append(Paragraph(
                        f"... and {len(warning_diffs) - 10} more warnings",
                        self.styles['Normal']
                    ))
                story.append(Spacer(1, 15))
            
            # Info
            if info_diffs:
                story.append(Paragraph(
                    f"<font color='#3b82f6'>● Info ({len(info_diffs)})</font>",
                    self.styles['Heading3']
                ))
                story.append(Spacer(1, 5))
                
                for diff in info_diffs[:5]:
                    story.append(self._create_difference_entry(diff, 'Info'))
                
                if len(info_diffs) > 5:
                    story.append(Paragraph(
                        f"... and {len(info_diffs) - 5} more info items",
                        self.styles['Normal']
                    ))
        else:
            story.append(Paragraph(
                "No differences found! The design and website match perfectly.",
                self.styles['Normal']
            ))
        
        # Footer
        story.append(Spacer(1, 40))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "Generated by Figma-Website UI Comparison Tool",
            self.styles['ReportSubtitle']
        ))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated: {output_path}")
        return str(output_path)
    
    def _create_difference_entry(self, diff, style_name: str) -> Paragraph:
        """Create a formatted difference entry."""
        text = f"<b>{diff.type.value}</b>: {diff.description or 'No description'}"
        if diff.figma_value and diff.website_value:
            text += f"<br/><font size='9'>Figma: {diff.figma_value} → Website: {diff.website_value}</font>"
        return Paragraph(text, self.styles[style_name])
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on match score."""
        if score >= 90:
            return '#10b981'  # Green
        elif score >= 70:
            return '#f59e0b'  # Yellow
        else:
            return '#dc2626'  # Red
