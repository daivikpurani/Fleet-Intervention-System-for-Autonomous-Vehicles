"""Ring buffer for per-vehicle state management.

Maintains a bounded in-memory ring buffer per vehicle_id with the last N frames.
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from services.schemas.events import RawTelemetryEvent

logger = logging.getLogger(__name__)

# Ring buffer size: last 10 frames
RING_BUFFER_SIZE = 10

# Out-of-order tolerance: allow events up to 500ms out of order
# This is a small bounded tolerance for event-time processing
OUT_OF_ORDER_TOLERANCE_MS = 500

# Event-time window: use frames within 1.0 seconds of latest frame
WINDOW_SECONDS = 1.0


class TelemetryFrame:
    """Single frame of telemetry data stored in ring buffer."""

    def __init__(self, event: RawTelemetryEvent):
        """Initialize frame from telemetry event.

        Args:
            event: RawTelemetryEvent to store
        """
        self.event_time = event.event_time
        self.frame_index = event.frame_index
        self.centroid = event.centroid
        self.velocity = event.velocity
        self.speed = event.speed
        self.yaw = event.yaw
        self.is_ego = event.is_ego
        self.track_id = event.track_id
        self.label_probabilities = event.label_probabilities


class VehicleState:
    """Per-vehicle state with ring buffer."""

    def __init__(self, vehicle_id: str):
        """Initialize vehicle state.

        Args:
            vehicle_id: Vehicle identifier
        """
        self.vehicle_id = vehicle_id
        self.ring_buffer: deque = deque(maxlen=RING_BUFFER_SIZE)
        self.last_frame_index: Optional[int] = None
        self.last_event_time: Optional[datetime] = None

    def add_frame(self, event: RawTelemetryEvent) -> bool:
        """Add a frame to the ring buffer.

        Handles out-of-order events within time-based tolerance.

        Args:
            event: RawTelemetryEvent to add

        Returns:
            True if frame was added, False if rejected (too far out of order)
        """
        # Check for out-of-order events using event_time
        if self.last_event_time is not None:
            time_diff = (event.event_time - self.last_event_time).total_seconds() * 1000  # Convert to ms

            # Reject events that are too far out of order (older than tolerance)
            if time_diff < -OUT_OF_ORDER_TOLERANCE_MS:
                logger.warning(
                    f"Rejecting out-of-order event for vehicle {self.vehicle_id}: "
                    f"event_time {event.event_time} is {abs(time_diff):.0f}ms behind last event_time {self.last_event_time}"
                )
                return False

        # Add frame to ring buffer
        frame = TelemetryFrame(event)
        self.ring_buffer.append(frame)

        # Update last seen frame and time
        self.last_frame_index = event.frame_index
        # Only update last_event_time if this event is newer
        if self.last_event_time is None or event.event_time > self.last_event_time:
            self.last_event_time = event.event_time

        return True

    def get_frames(self) -> List[TelemetryFrame]:
        """Get all frames in the ring buffer.

        Returns:
            List of TelemetryFrame objects (ordered by insertion, oldest first)
        """
        return list(self.ring_buffer)

    def get_frames_in_window(self) -> List[TelemetryFrame]:
        """Get frames within event-time window of latest frame.

        Uses WINDOW_SECONDS to filter frames by event_time.

        Returns:
            List of TelemetryFrame objects within window (ordered by event_time, oldest first)
        """
        if not self.ring_buffer or self.last_event_time is None:
            return []

        # Calculate window start time
        window_start = self.last_event_time - timedelta(seconds=WINDOW_SECONDS)

        # Filter frames within window
        frames_in_window = [
            frame
            for frame in self.ring_buffer
            if frame.event_time >= window_start
        ]

        # Sort by event_time (oldest first)
        frames_in_window.sort(key=lambda f: f.event_time)

        return frames_in_window

    def has_sufficient_history(self, min_frames: int = 2) -> bool:
        """Check if ring buffer has sufficient history within window.

        Args:
            min_frames: Minimum number of frames required

        Returns:
            True if buffer has at least min_frames frames within window
        """
        frames_in_window = self.get_frames_in_window()
        return len(frames_in_window) >= min_frames


class StateManager:
    """Manages per-vehicle state with ring buffers."""

    def __init__(self):
        """Initialize state manager."""
        self.vehicles: Dict[str, VehicleState] = {}

    def get_or_create_vehicle(self, vehicle_id: str) -> VehicleState:
        """Get or create vehicle state.

        Args:
            vehicle_id: Vehicle identifier

        Returns:
            VehicleState for the vehicle
        """
        if vehicle_id not in self.vehicles:
            self.vehicles[vehicle_id] = VehicleState(vehicle_id)
        return self.vehicles[vehicle_id]

    def update_vehicle(self, event: RawTelemetryEvent) -> bool:
        """Update vehicle state with new telemetry event.

        Args:
            event: RawTelemetryEvent to add

        Returns:
            True if event was added, False if rejected
        """
        vehicle_state = self.get_or_create_vehicle(event.vehicle_id)
        return vehicle_state.add_frame(event)

    def get_vehicle_state(self, vehicle_id: str) -> Optional[VehicleState]:
        """Get vehicle state.

        Args:
            vehicle_id: Vehicle identifier

        Returns:
            VehicleState if exists, None otherwise
        """
        return self.vehicles.get(vehicle_id)
