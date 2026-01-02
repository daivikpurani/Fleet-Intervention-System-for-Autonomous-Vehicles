"""Feature extraction from telemetry ring buffer.

Extracts features needed for anomaly detection:
- Instantaneous acceleration (Δspeed / Δtime)
- Jerk proxy (Δacceleration)
- Centroid displacement per frame
- Heading change proxy (Δyaw)
- Active agent count (global, per frame_index)
"""

import logging
import math
from typing import Dict, List, Optional

from .windows import TelemetryFrame

logger = logging.getLogger(__name__)

# Maximum time delta for valid transitions (0.5 seconds)
MAX_DT_SECONDS = 0.5


class FeatureExtractor:
    """Extracts features from telemetry ring buffer."""

    def __init__(self):
        """Initialize feature extractor."""
        # Global active agent count per frame_index
        # Updated by main processing loop
        self.active_agent_count: Dict[int, int] = {}

    def update_active_agent_count(self, frame_index: int, count: int) -> None:
        """Update active agent count for a frame.

        Args:
            frame_index: Frame index
            count: Number of active agents in this frame
        """
        self.active_agent_count[frame_index] = count

    def get_active_agent_count(self, frame_index: int) -> Optional[int]:
        """Get active agent count for a frame.

        Args:
            frame_index: Frame index

        Returns:
            Active agent count if available, None otherwise
        """
        return self.active_agent_count.get(frame_index)

    def extract_acceleration(self, frames: List[TelemetryFrame]) -> Optional[float]:
        """Extract instantaneous acceleration from last two frames.

        Acceleration = Δspeed / Δtime

        Args:
            frames: List of TelemetryFrame objects (ordered, oldest first)

        Returns:
            Acceleration in m/s² if sufficient history, None otherwise
        """
        if len(frames) < 2:
            return None

        # Get last two frames
        prev_frame = frames[-2]
        curr_frame = frames[-1]

        # Calculate time delta in seconds
        dt = (curr_frame.event_time - prev_frame.event_time).total_seconds()
        
        # Safety guard: skip if dt is invalid
        if dt <= 0 or dt > MAX_DT_SECONDS:
            return None

        # Calculate speed delta
        dspeed = curr_frame.speed - prev_frame.speed

        # Acceleration = Δspeed / Δtime
        acceleration = dspeed / dt
        return acceleration

    def extract_jerk_proxy(self, frames: List[TelemetryFrame]) -> Optional[float]:
        """Extract jerk proxy (change in acceleration).

        Jerk proxy = Δacceleration

        Args:
            frames: List of TelemetryFrame objects (ordered, oldest first)

        Returns:
            Jerk proxy in m/s³ if sufficient history, None otherwise
        """
        if len(frames) < 3:
            return None

        # Get last three frames
        prev_prev_frame = frames[-3]
        prev_frame = frames[-2]
        curr_frame = frames[-1]

        # Calculate accelerations
        dt1 = (prev_frame.event_time - prev_prev_frame.event_time).total_seconds()
        dt2 = (curr_frame.event_time - prev_frame.event_time).total_seconds()

        # Safety guard: skip if dt is invalid
        if dt1 <= 0 or dt1 > MAX_DT_SECONDS or dt2 <= 0 or dt2 > MAX_DT_SECONDS:
            return None

        accel1 = (prev_frame.speed - prev_prev_frame.speed) / dt1
        accel2 = (curr_frame.speed - prev_frame.speed) / dt2

        # Jerk proxy = Δacceleration / Δtime
        jerk = (accel2 - accel1) / dt2
        return jerk

    def extract_centroid_displacement(
        self, frames: List[TelemetryFrame]
    ) -> Optional[float]:
        """Extract centroid displacement per frame.

        Displacement = distance between consecutive centroids

        Args:
            frames: List of TelemetryFrame objects (ordered, oldest first)

        Returns:
            Displacement in meters if sufficient history, None otherwise
        """
        if len(frames) < 2:
            return None

        # Get last two frames
        prev_frame = frames[-2]
        curr_frame = frames[-1]

        # Calculate Euclidean distance
        dx = curr_frame.centroid["x"] - prev_frame.centroid["x"]
        dy = curr_frame.centroid["y"] - prev_frame.centroid["y"]
        displacement = math.sqrt(dx * dx + dy * dy)

        return displacement

    def extract_heading_change(
        self, frames: List[TelemetryFrame]
    ) -> Optional[float]:
        """Extract heading change proxy (Δyaw).

        Args:
            frames: List of TelemetryFrame objects (ordered, oldest first)

        Returns:
            Heading change in radians if sufficient history, None otherwise
        """
        if len(frames) < 2:
            return None

        # Get last two frames
        prev_frame = frames[-2]
        curr_frame = frames[-1]

        if prev_frame.yaw is None or curr_frame.yaw is None:
            return None

        # Calculate yaw change (handle wrap-around)
        dyaw = curr_frame.yaw - prev_frame.yaw

        # Normalize to [-π, π]
        while dyaw > math.pi:
            dyaw -= 2 * math.pi
        while dyaw < -math.pi:
            dyaw += 2 * math.pi

        return abs(dyaw)

    def extract_all_features(
        self, frames: List[TelemetryFrame], frame_index: int
    ) -> Dict[str, Optional[float]]:
        """Extract all features from ring buffer.

        Args:
            frames: List of TelemetryFrame objects
            frame_index: Current frame index (for active agent count)

        Returns:
            Dictionary of feature names to values
        """
        features = {
            "acceleration": self.extract_acceleration(frames),
            "jerk_proxy": self.extract_jerk_proxy(frames),
            "centroid_displacement": self.extract_centroid_displacement(frames),
            "heading_change": self.extract_heading_change(frames),
            "active_agent_count": self.get_active_agent_count(frame_index),
        }

        return features
