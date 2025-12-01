"""Report generation service for comparison results."""

from typing import Dict
from pathlib import Path
import json
from datetime import datetime, timezone
from jinja2 import Template
import logging

from ..models.schemas import DiffReport

logger = logging.getLogger(__name__)


def format_local_datetime(dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Convert datetime to local timezone and format it."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone()  # Convert to local timezone
    return local_dt.strftime(fmt)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UI Comparison Report - {{ report.job_id }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px 8px 0 0;
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f9fafb;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .summary-card.critical { border-left-color: #ef4444; }
        .summary-card.warning { border-left-color: #f59e0b; }
        .summary-card.info { border-left-color: #3b82f6; }
        .summary-card h3 { font-size: 14px; color: #6b7280; text-transform: uppercase; margin-bottom: 5px; }
        .summary-card .value { font-size: 32px; font-weight: bold; color: #111827; }
        .screenshots {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .screenshot-card {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .screenshot-card h3 {
            padding: 15px;
            background: #f9fafb;
            border-bottom: 1px solid #e5e7eb;
            font-size: 16px;
        }
        .screenshot-card img { width: 100%; display: block; }
        .differences {
            padding: 30px;
        }
        .differences h2 {
            font-size: 24px;
            margin-bottom: 20px;
            color: #111827;
        }
        .difference-item {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }
        .difference-item.critical { border-left: 4px solid #ef4444; }
        .difference-item.warning { border-left: 4px solid #f59e0b; }
        .difference-item.info { border-left: 4px solid #3b82f6; }
        .diff-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .diff-type {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .diff-type.color { background: #dbeafe; color: #1e40af; }
        .diff-type.typography { background: #fce7f3; color: #9f1239; }
        .diff-type.spacing { background: #d1fae5; color: #065f46; }
        .diff-type.dimension { background: #fef3c7; color: #92400e; }
        .diff-type.layout { background: #e0e7ff; color: #3730a3; }
        .diff-type.visual { background: #f3e8ff; color: #6b21a8; }
        .severity {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .severity.critical { background: #fee2e2; color: #991b1b; }
        .severity.warning { background: #fef3c7; color: #92400e; }
        .severity.info { background: #dbeafe; color: #1e40af; }
        .diff-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        .diff-value {
            background: #f9fafb;
            padding: 12px;
            border-radius: 6px;
        }
        .diff-value h4 {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        .diff-value p {
            font-size: 14px;
            color: #111827;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        .match-score {
            text-align: center;
            padding: 30px;
            background: #f9fafb;
        }
        .score-circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: conic-gradient(#10b981 0% {{ report.summary.match_score }}%, #e5e7eb {{ report.summary.match_score }}% 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            position: relative;
        }
        .score-circle::before {
            content: '';
            width: 120px;
            height: 120px;
            background: white;
            border-radius: 50%;
            position: absolute;
        }
        .score-value {
            position: relative;
            font-size: 36px;
            font-weight: bold;
            color: #111827;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 UI Comparison Report</h1>
            <p>Job ID: {{ report.job_id }} | Generated: {{ local_time }}</p>
        </div>
        
        <div class="match-score">
            <h2>Overall Match Score</h2>
            <div class="score-circle">
                <span class="score-value">{{ "%.1f"|format(report.summary.match_score) }}%</span>
            </div>
            <p>Based on visual similarity and structural comparison</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Differences</h3>
                <div class="value">{{ report.summary.total_differences }}</div>
            </div>
            <div class="summary-card critical">
                <h3>Critical Issues</h3>
                <div class="value">{{ report.summary.critical }}</div>
            </div>
            <div class="summary-card warning">
                <h3>Warnings</h3>
                <div class="value">{{ report.summary.warnings }}</div>
            </div>
            <div class="summary-card info">
                <h3>Info</h3>
                <div class="value">{{ report.summary.info }}</div>
            </div>
        </div>
        
        {% if report.figma_screenshot_url or report.website_screenshot_url %}
        <div class="screenshots">
            {% if report.figma_screenshot_url %}
            <div class="screenshot-card">
                <h3>📐 Figma Design</h3>
                <img src="{{ report.figma_screenshot_url }}" alt="Figma Design">
            </div>
            {% endif %}
            
            {% if report.website_screenshot_url %}
            <div class="screenshot-card">
                <h3>🌐 Website</h3>
                <img src="{{ report.website_screenshot_url }}" alt="Website">
            </div>
            {% endif %}
        </div>
        {% endif %}
        
        {% if report.differences %}
        <div class="differences">
            <h2>Detected Differences ({{ report.differences|length }})</h2>
            
            {% for diff in report.differences %}
            <div class="difference-item {{ diff.severity }}">
                <div class="diff-header">
                    <span class="diff-type {{ diff.type }}">{{ diff.type }}</span>
                    <span class="severity {{ diff.severity }}">{{ diff.severity }}</span>
                </div>
                <p style="margin: 10px 0; color: #374151;">{{ diff.description }}</p>
                
                {% if diff.figma_value or diff.website_value %}
                <div class="diff-details">
                    <div class="diff-value">
                        <h4>Figma Design</h4>
                        <p>{{ diff.figma_value or 'N/A' }}</p>
                    </div>
                    <div class="diff-value">
                        <h4>Website Implementation</h4>
                        <p>{{ diff.website_value or 'N/A' }}</p>
                    </div>
                </div>
                {% endif %}
                
                {% if diff.delta %}
                <p style="margin-top: 10px; color: #6b7280; font-size: 14px;">
                    <strong>Delta:</strong> {{ diff.delta }}
                </p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


class ReportGenerator:
    """Generate comparison reports in various formats."""
    
    def __init__(self):
        """Initialize report generator."""
        self.html_template = Template(HTML_TEMPLATE)
    
    def generate_json_report(self, report: DiffReport, output_path: Path) -> str:
        """
        Generate JSON report.
        
        Args:
            report: Difference report
            output_path: Path to save JSON report
            
        Returns:
            Path to saved report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        report_dict = report.model_dump(mode='json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info(f"JSON report saved: {output_path}")
        return str(output_path)
    
    def generate_html_report(self, report: DiffReport, output_path: Path) -> str:
        """
        Generate HTML report.
        
        Args:
            report: Difference report
            output_path: Path to save HTML report
            
        Returns:
            Path to saved report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Render template with local time
        local_time = format_local_datetime(report.created_at)
        html_content = self.html_template.render(report=report, local_time=local_time)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved: {output_path}")
        return str(output_path)
    
    def generate_summary_text(self, report: DiffReport) -> str:
        """
        Generate plain text summary.
        
        Args:
            report: Difference report
            
        Returns:
            Text summary
        """
        summary = report.summary
        
        text = f"""
UI Comparison Report
===================
Job ID: {report.job_id}
Status: {report.status}
Generated: {report.created_at}

Overall Match Score: {summary.match_score:.1f}%

Summary:
--------
Total Differences: {summary.total_differences}
  - Critical: {summary.critical}
  - Warnings: {summary.warnings}
  - Info: {summary.info}

Top Issues:
-----------
"""
        
        # Add top critical and warning differences
        critical_diffs = [d for d in report.differences if d.severity == "critical"][:5]
        warning_diffs = [d for d in report.differences if d.severity == "warning"][:5]
        
        if critical_diffs:
            text += "\nCritical Issues:\n"
            for diff in critical_diffs:
                text += f"  - {diff.description}\n"
        
        if warning_diffs:
            text += "\nWarnings:\n"
            for diff in warning_diffs:
                text += f"  - {diff.description}\n"
        
        return text
