"""Telemetry normalization.

Normalizes L5Kit dataset format to internal telemetry format.
Enforces strict invariants:
- Agent centroid is [x, y] → output {x, y, z: 0.0}
- Agent velocity is [vx, vy]
- Speed = sqrt(vx² + vy²)
- Ego velocity derived from position deltas + timestamps
- Ego extent is synthetic constant, clearly documented
- label_probabilities used only as classification stability proxy
"""

import logging
import math
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Synthetic ego extent constants (clearly documented)
# These are synthetic values since L5Kit dataset doesn't provide ego extent
# Used for consistency in telemetry output
EGO_LENGTH_M = 4.5  # Typical sedan length in meters
EGO_WIDTH_M = 1.8   # Typical sedan width in meters
EGO_HEIGHT_M = 1.5  # Typical sedan height in meters

# Ego displacement guard for dataset discontinuity detection
# L5Kit dataset can have large single-frame jumps due to scene stitching,
# coordinate frame resets, or dataset segmentation boundaries
MAX_EGO_DISPLACEMENT_PER_FRAME = 20.0  # meters, dataset discontinuity guard


class TelemetryNormalizer:
    """Normalizes L5Kit agent/ego data to internal telemetry format.
    
    Enforces strict invariants:
    - Centroid must be 2D [x, y] (assertion failure if violated)
    - Velocity must be 2D [vx, vy] (assertion failure if violated)
    - Fails fast on invariant violations
    """

    def __init__(self):
        """Initialize normalizer."""
        pass

    def normalize_agent(self, agent_data: np.ndarray, track_id: int) -> Dict:
        """Normalize agent data to internal format.
        
        Args:
            agent_data: Single agent record from L5Kit agents array
            track_id: Track ID for this agent
            
        Returns:
            Normalized agent telemetry dictionary with:
            - centroid: {x, y, z: 0.0}
            - velocity: {vx, vy}
            - speed: scalar speed in m/s
            - yaw: orientation in radians (if available)
            - label_probabilities: classification probabilities (if available)
            
        Raises:
            AssertionError: If centroid or velocity are not 2D
        """
        # Extract centroid - must be 2D [x, y]
        dtype_names = agent_data.dtype.names if hasattr(agent_data.dtype, 'names') and agent_data.dtype.names else None
        if dtype_names is None or 'centroid' not in dtype_names:
            raise ValueError("'centroid' field not found in agent data")
        
        centroid = agent_data['centroid']
        
        # CRITICAL ASSERTION: Centroid must be 2D [x, y]
        # Fail fast if violated
        assert len(centroid.shape) == 1, f"Centroid must be 1D array, got shape {centroid.shape}"
        assert centroid.shape[0] == 2, f"Centroid must be [x, y] (length 2), got length {centroid.shape[0]}"
        
        # Extract velocity - must be 2D [vx, vy]
        if 'velocity' not in dtype_names:
            raise ValueError("'velocity' field not found in agent data")
        
        velocity = agent_data['velocity']
        
        # CRITICAL ASSERTION: Velocity must be 2D [vx, vy]
        # Fail fast if violated
        assert len(velocity.shape) == 1, f"Velocity must be 1D array, got shape {velocity.shape}"
        assert velocity.shape[0] == 2, f"Velocity must be [vx, vy] (length 2), got length {velocity.shape[0]}"
        
        # Normalize centroid: [x, y] → {x, y, z: 0.0}
        normalized_centroid = {
            'x': float(centroid[0]),
            'y': float(centroid[1]),
            'z': 0.0,  # Always 0.0 for 2D positions
        }
        
        # Normalize velocity: [vx, vy] → {vx, vy}
        vx = float(velocity[0])
        vy = float(velocity[1])
        normalized_velocity = {
            'vx': vx,
            'vy': vy,
        }
        
        # Compute speed: sqrt(vx² + vy²)
        speed = math.sqrt(vx * vx + vy * vy)
        
        # Extract yaw if available
        yaw = None
        if 'yaw' in dtype_names:
            yaw = float(agent_data['yaw'])
        
        # Extract label_probabilities if available
        # Used only as classification stability proxy (not calibrated confidence)
        label_probabilities = None
        if 'label_probabilities' in dtype_names:
            probs = agent_data['label_probabilities']
            # Convert to list of floats
            if probs is not None and len(probs) > 0:
                label_probabilities = [float(p) for p in probs]
        
        return {
            'centroid': normalized_centroid,
            'velocity': normalized_velocity,
            'speed': speed,
            'yaw': yaw,
            'label_probabilities': label_probabilities,
            'track_id': track_id,
        }

    def normalize_ego(
        self,
        ego_data: Dict,
        previous_ego_data: Optional[Dict],
        frame_timestamp: int,
        previous_frame_timestamp: Optional[int],
    ) -> Dict:
        """Normalize ego vehicle data to internal format.
        
        Ego velocity is derived from position deltas + timestamps.
        Ego extent is synthetic constant (documented above).
        
        Args:
            ego_data: Ego data from get_ego_data()
            previous_ego_data: Previous frame's normalized ego data (for velocity calculation)
            frame_timestamp: Current frame timestamp (nanoseconds)
            previous_frame_timestamp: Previous frame timestamp (nanoseconds)
            
        Returns:
            Normalized ego telemetry dictionary with:
            - centroid: {x, y, z: 0.0}
            - velocity: {vx, vy} (derived from position deltas)
            - speed: scalar speed in m/s
            - yaw: orientation in radians (if available)
            - extent: {length, width, height} (synthetic constants)
        """
        agent_data = ego_data['data']
        
        # Normalize centroid (same as agent)
        dtype_names = agent_data.dtype.names if hasattr(agent_data.dtype, 'names') and agent_data.dtype.names else None
        if dtype_names is None or 'centroid' not in dtype_names:
            raise ValueError("'centroid' field not found in ego data")
        
        centroid = agent_data['centroid']
        
        # CRITICAL ASSERTION: Centroid must be 2D [x, y]
        assert len(centroid.shape) == 1, f"Ego centroid must be 1D array, got shape {centroid.shape}"
        assert centroid.shape[0] == 2, f"Ego centroid must be [x, y] (length 2), got length {centroid.shape[0]}"
        
        normalized_centroid = {
            'x': float(centroid[0]),
            'y': float(centroid[1]),
            'z': 0.0,
        }
        
        # Derive velocity from position deltas + timestamps
        if previous_ego_data is not None and previous_frame_timestamp is not None:
            # Calculate time delta in seconds
            dt_ns = frame_timestamp - previous_frame_timestamp
            dt_seconds = dt_ns / 1e9
            
            if dt_seconds > 0:
                # Calculate position delta
                dx = normalized_centroid['x'] - previous_ego_data['centroid']['x']
                dy = normalized_centroid['y'] - previous_ego_data['centroid']['y']
                
                # Compute planar displacement for discontinuity detection
                displacement = math.sqrt(dx * dx + dy * dy)
                
                # Displacement guard: detect pose discontinuities (scene stitching, coordinate resets)
                if displacement > MAX_EGO_DISPLACEMENT_PER_FRAME:
                    # Treat as discontinuity - reset velocity to zero
                    vx = 0.0
                    vy = 0.0
                else:
                    # Normal motion - derive velocity from delta
                    vx = dx / dt_seconds
                    vy = dy / dt_seconds
            else:
                # Zero or negative time delta - use zero velocity
                vx = 0.0
                vy = 0.0
        else:
            # No previous frame - try to use velocity from dataset if available
            if 'velocity' in dtype_names:
                velocity = agent_data['velocity']
                # CRITICAL ASSERTION: Velocity must be 2D [vx, vy]
                assert len(velocity.shape) == 1, f"Ego velocity must be 1D array, got shape {velocity.shape}"
                assert velocity.shape[0] == 2, f"Ego velocity must be [vx, vy] (length 2), got length {velocity.shape[0]}"
                vx = float(velocity[0])
                vy = float(velocity[1])
            else:
                # No velocity data available - use zero
                vx = 0.0
                vy = 0.0
        
        normalized_velocity = {
            'vx': vx,
            'vy': vy,
        }
        
        # Compute speed: sqrt(vx² + vy²)
        speed = math.sqrt(vx * vx + vy * vy)
        
        # Extract yaw if available
        yaw = None
        if 'yaw' in dtype_names:
            yaw = float(agent_data['yaw'])
        
        # Synthetic ego extent (clearly documented constants)
        extent = {
            'length': EGO_LENGTH_M,
            'width': EGO_WIDTH_M,
            'height': EGO_HEIGHT_M,
        }
        
        return {
            'centroid': normalized_centroid,
            'velocity': normalized_velocity,
            'speed': speed,
            'yaw': yaw,
            'extent': extent,
        }
