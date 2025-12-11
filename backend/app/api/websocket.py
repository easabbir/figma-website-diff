"""WebSocket endpoint for real-time progress updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging

from app.models.schemas import ProgressUpdate
from app.services.job_storage import job_storage
from app.core.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    
    Args:
        websocket: WebSocket connection
        job_id: Job identifier to monitor
    """
    await websocket_manager.connect(job_id, websocket)
    
    try:
        # Send initial progress
        progress = job_storage.get_progress(job_id)
        if progress:
            await websocket_manager.send_progress(job_id, progress)
        
        # Keep connection alive and send updates
        while True:
            # Check for progress updates every second
            await asyncio.sleep(1)
            
            progress = job_storage.get_progress(job_id)
            if progress:
                await websocket_manager.send_progress(job_id, progress)
                
                # Close connection if job is completed or failed
                if progress.status in ["completed", "failed"]:
                    logger.info(f"Job {job_id} finished with status: {progress.status}")
                    break
            else:
                # Job not found
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "not_found",
                    "message": "Job not found"
                })
                break
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        websocket_manager.disconnect(job_id)
