"""
WebSocket handler for real-time updates - Limited in CLI Bridge mode.

In CLI Bridge mode, real-time progress is not available since the CLI
executes independently. This module provides basic WebSocket connectivity
for potential future enhancements.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections - Limited functionality in CLI Bridge mode."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "connected_at": datetime.utcnow(),
            "client_info": {
                "client": websocket.client.host if websocket.client else "unknown",
                "user_agent": websocket.headers.get("user-agent", "unknown")
            }
        }
        
        logger.info("WebSocket connected (CLI Bridge mode - limited functionality)")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        self.connection_metadata.pop(websocket, None)
        logger.info("WebSocket disconnected")
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def get_connection_count(self) -> dict:
        """Get current connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "mode": "cli_bridge",
            "real_time_progress": False,
            "message": "Real-time progress not available in CLI Bridge mode"
        }


# Global connection manager instance
connection_manager = ConnectionManager()


@router.websocket("/progress")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint - Limited functionality in CLI Bridge mode.
    
    In CLI Bridge mode, real-time progress updates are not available
    since the CLI executes independently. This endpoint provides basic
    connectivity for system messages and connection status.
    """
    await connection_manager.connect(websocket)
    
    try:
        # Send initial connection message
        await connection_manager.send_message(websocket, {
            "type": "connection_established",
            "data": {
                "mode": "cli_bridge",
                "message": "Connected to AutoTrainX WebSocket (CLI Bridge mode)",
                "limitations": [
                    "Real-time job progress not available",
                    "Job updates must be polled via REST API",
                    "CLI executes independently"
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle ping/pong
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await connection_manager.send_message(websocket, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message.get("type") == "get_stats":
                    stats = connection_manager.get_connection_count()
                    await connection_manager.send_message(websocket, {
                        "type": "connection_stats",
                        "data": stats,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    await connection_manager.send_message(websocket, {
                        "type": "info",
                        "data": {
                            "message": "WebSocket is connected but real-time progress is not available in CLI Bridge mode"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await connection_manager.send_message(websocket, {
                    "type": "error",
                    "data": {"message": "Invalid JSON message"},
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(websocket)


@router.websocket("/progress/{job_id}")
async def websocket_job_endpoint(
    websocket: WebSocket,
    job_id: str
):
    """
    Job-specific WebSocket endpoint - Not functional in CLI Bridge mode.
    
    Real-time job progress is not available since jobs are executed
    independently by the CLI. Use the REST API to poll job status instead.
    """
    await websocket.accept()
    
    try:
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {
                "message": "Job-specific WebSocket connections are not supported in CLI Bridge mode",
                "job_id": job_id,
                "suggestion": "Use GET /api/v1/jobs/{job_id} to poll job status"
            },
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Close connection immediately
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Job progress WebSocket not supported in CLI Bridge mode"
        )
        
    except Exception as e:
        logger.error(f"Error in job WebSocket: {e}")


@router.get("/connections/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics."""
    return {
        "success": True,
        "data": connection_manager.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/broadcast/system")
async def broadcast_system_message(
    message_type: str,
    data: dict
):
    """
    Broadcast a system message to all connected clients.
    
    This is one of the few WebSocket features that remains functional
    in CLI Bridge mode for system-wide notifications.
    """
    try:
        await connection_manager.broadcast({
            "type": message_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
        return {
            "success": True,
            "message": f"System message '{message_type}' broadcast successfully",
            "recipients": connection_manager.get_connection_count(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health")
async def websocket_health_check():
    """Check health of WebSocket service."""
    try:
        stats = connection_manager.get_connection_count()
        return {
            "status": "healthy",
            "service": "websockets",
            "mode": "cli_bridge",
            "connection_stats": stats,
            "features": {
                "job_specific_connections": False,
                "real_time_progress": False,
                "system_messaging": True,
                "basic_connectivity": True
            },
            "message": "WebSocket service operational (CLI Bridge mode - limited features)"
        }
    except Exception as e:
        logger.error(f"WebSocket service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "websockets",
            "error": str(e),
            "message": "WebSocket service is not operational"
        }