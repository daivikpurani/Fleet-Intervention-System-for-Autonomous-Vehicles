"""WebSocket manager for broadcasting alerts and vehicle updates."""

import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manager for WebSocket connections and broadcasting."""

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast a message to all connected WebSocket clients.

        Message format:
        {
            "type": "<event_type>",
            "data": { ... }
        }

        Args:
            event_type: Type of event (alert_created, alert_updated, vehicle_updated, operator_action_created)
            data: Event data
        """
        if not self.active_connections:
            return

        message = {
            "type": event_type,
            "data": data,
        }

        message_json = json.dumps(message, default=str)

        # Send to all connections, removing dead ones
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(connection)

        # Remove dead connections
        for connection in disconnected:
            self.disconnect(connection)

        logger.debug(f"Broadcasted {event_type} to {len(self.active_connections)} connections")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
