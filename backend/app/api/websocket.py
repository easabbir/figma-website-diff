"""WebSocket endpoint for real-time progress updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import logging

from ..models.schemas import ProgressUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

# Import job progress from endpoints
from .endpoints import job_progress


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, job_id: str, websocket: WebSocket):
        """Connect a websocket for a specific job."""
        await websocket.accept()
        self.active_connections[job_id] = websocket
        logger.info(f"WebSocket connected for job {job_id}")
    
    def disconnect(self, job_id: str):
        """Disconnect a websocket."""
        if job_id in self.active_connections:
            del self.active_connections[job_id]
            logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def send_progress(self, job_id: str, progress: ProgressUpdate):
        """Send progress update to connected client."""
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_json(
                    progress.model_dump(mode='json')
                )
            except Exception as e:
                logger.error(f"Error sending progress for job {job_id}: {e}")
                self.disconnect(job_id)


manager = ConnectionManager()


@router.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    
    Args:
        websocket: WebSocket connection
        job_id: Job identifier to monitor
    """
    await manager.connect(job_id, websocket)
    
    try:
        # Send initial progress
        if job_id in job_progress:
            await manager.send_progress(job_id, job_progress[job_id])
        
        # Keep connection alive and send updates
        while True:
            # Check for progress updates every second
            await asyncio.sleep(1)
            
            if job_id in job_progress:
                progress = job_progress[job_id]
                await manager.send_progress(job_id, progress)
                
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
        manager.disconnect(job_id)
