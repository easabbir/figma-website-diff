"""Background tasks module."""

from app.tasks.comparison_tasks import process_comparison_job, process_responsive_comparison

__all__ = ["process_comparison_job", "process_responsive_comparison"]
