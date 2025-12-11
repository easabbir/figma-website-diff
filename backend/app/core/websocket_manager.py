"""WebSocket connection manager for real-time progress updates."""

from fastapi import WebSocket
from typing import Dict
import logging

from app.models.schemas import ProgressUpdate

logger = logging.getLogger(__name__)


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


websocket_manager = ConnectionManager()
