"""L5Kit zarr dataset reader.

Loads L5Kit dataset via zarr and provides access to scenes and frames.
Does not preload full arrays - uses lazy zarr access.
"""

import logging
from pathlib import Path
from typing import List, Tuple

import numpy as np
import zarr

logger = logging.getLogger(__name__)


class DatasetReader:
    """Reader for L5Kit zarr dataset format.
    
    Supports sample.zarr explicitly.
    Does not preload full arrays - uses lazy zarr access.
    Does not assume 3D centroids - handles 2D [x, y] format.
    """

    def __init__(self, dataset_path: str):
        """Initialize dataset reader.
        
        Args:
            dataset_path: Path to zarr dataset (e.g., sample.zarr)
        """
        self.dataset_path = Path(dataset_path)
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")
        
        # Open zarr dataset in read-only mode
        self.root = zarr.open(str(self.dataset_path), mode='r')
        
        # Verify required arrays exist
        if 'scenes' not in self.root:
            raise ValueError("'scenes' array not found in dataset")
        if 'frames' not in self.root:
            raise ValueError("'frames' array not found in dataset")
        if 'agents' not in self.root:
            raise ValueError("'agents' array not found in dataset")
        
        self.scenes = self.root['scenes']
        self.frames = self.root['frames']
        self.agents = self.root['agents']
        
        logger.info(f"Loaded dataset from {dataset_path}")
        logger.info(f"Scenes: {len(self.scenes)}, Frames: {len(self.frames)}, Agents: {len(self.agents)}")

    def list_scenes(self) -> List[int]:
        """List all available scene IDs.
        
        Returns:
            List of scene indices (0-based)
        """
        # Check if frame_index_interval field exists
        dtype_names = self.scenes.dtype.names if hasattr(self.scenes.dtype, 'names') and self.scenes.dtype.names else None
        if dtype_names is None or 'frame_index_interval' not in dtype_names:
            raise ValueError("'frame_index_interval' not found in scenes array")
        
        intervals = self.scenes['frame_index_interval']
        num_scenes = len(intervals)
        
        return list(range(num_scenes))

    def get_scene_frames(self, scene_id: int) -> Tuple[int, int]:
        """Get frame index range for a scene.
        
        Args:
            scene_id: Scene index (0-based)
            
        Returns:
            Tuple of (start_frame_index, end_frame_index)
            end_frame_index is exclusive (like Python range)
        """
        dtype_names = self.scenes.dtype.names if hasattr(self.scenes.dtype, 'names') and self.scenes.dtype.names else None
        if dtype_names is None or 'frame_index_interval' not in dtype_names:
            raise ValueError("'frame_index_interval' not found in scenes array")
        
        intervals = self.scenes['frame_index_interval']
        
        if scene_id < 0 or scene_id >= len(intervals):
            raise IndexError(f"Scene ID {scene_id} out of range [0, {len(intervals)})")
        
        start_frame, end_frame = intervals[scene_id]
        return (start_frame, end_frame)

    def get_frame_data(self, frame_index: int) -> dict:
        """Get data for a specific frame.
        
        Args:
            frame_index: Frame index (0-based)
            
        Returns:
            Dictionary containing:
            - timestamp: Frame timestamp (nanoseconds)
            - agent_index_interval: (start_agent_idx, end_agent_idx)
            - agents: Agent data for this frame (lazy zarr array slice)
        """
        if frame_index < 0 or frame_index >= len(self.frames):
            raise IndexError(f"Frame index {frame_index} out of range [0, {len(self.frames)})")
        
        # Get frame metadata
        dtype_names = self.frames.dtype.names if hasattr(self.frames.dtype, 'names') and self.frames.dtype.names else None
        if dtype_names is None:
            raise ValueError("Frames array does not have named fields")
        
        frame = self.frames[frame_index]
        
        # Extract timestamp
        if 'timestamp' not in dtype_names:
            raise ValueError("'timestamp' field not found in frames array")
        timestamp = int(frame['timestamp'])
        
        # Extract agent index interval
        if 'agent_index_interval' not in dtype_names:
            raise ValueError("'agent_index_interval' field not found in frames array")
        agent_start, agent_end = frame['agent_index_interval']
        
        # Get agent data slice (lazy - not loaded into memory)
        agents_slice = self.agents[agent_start:agent_end]
        
        return {
            'timestamp': timestamp,
            'agent_index_interval': (agent_start, agent_end),
            'agents': agents_slice,
        }

    def get_ego_data(self, frame_index: int) -> dict:
        """Get ego vehicle data for a specific frame.
        
        Note: L5Kit dataset may not have explicit ego data in all frames.
        This method attempts to find ego data, but may return None if not available.
        
        Args:
            frame_index: Frame index (0-based)
            
        Returns:
            Dictionary containing ego data, or None if not available.
            Structure matches agent data format.
        """
        # For now, we'll derive ego from frame data
        # In L5Kit, ego is typically the first agent or identified by track_id
        # This is a placeholder - actual implementation depends on dataset structure
        frame_data = self.get_frame_data(frame_index)
        agents = frame_data['agents']
        
        if len(agents) == 0:
            return None
        
        # Check if agents have track_id field to identify ego
        dtype_names = agents.dtype.names if hasattr(agents.dtype, 'names') and agents.dtype.names else None
        if dtype_names and 'track_id' in dtype_names:
            # Ego typically has track_id == -1 or is the first agent
            # This is dataset-specific and may need adjustment
            for i, agent in enumerate(agents):
                if agent['track_id'] == -1:
                    return {
                        'agent_index': frame_data['agent_index_interval'][0] + i,
                        'data': agent,
                    }
        
        # Fallback: use first agent as ego
        return {
            'agent_index': frame_data['agent_index_interval'][0],
            'data': agents[0],
        }
