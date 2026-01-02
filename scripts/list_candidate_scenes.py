#!/usr/bin/env python3
"""
List Candidate Scenes Script

Iterates through scenes in the L5Kit dataset and prints summary statistics.
Used for inspection only - no golden scene selection in Phase 0.
"""

import sys
import os
from pathlib import Path

try:
    import zarr
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing required dependency: {e}")
    print("Install with: pip install zarr numpy")
    sys.exit(1)


def load_dataset(dataset_path):
    """Load the zarr dataset."""
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        print(f"ERROR: Dataset path does not exist: {dataset_path}")
        sys.exit(1)
    
    try:
        root = zarr.open(str(dataset_path), mode='r')
        return root
    except Exception as e:
        print(f"ERROR: Cannot open zarr dataset: {e}")
        sys.exit(1)


def get_scene_frame_count(scenes, scene_idx):
    """Get the number of frames in a scene."""
    # Check if field exists in structured array dtype
    dtype_names = scenes.dtype.names if hasattr(scenes.dtype, 'names') and scenes.dtype.names else None
    if dtype_names is None or 'frame_index_interval' not in dtype_names:
        return None
    
    intervals = scenes['frame_index_interval']
    if scene_idx >= len(intervals):
        return None
    
    start_frame, end_frame = intervals[scene_idx]
    return end_frame - start_frame


def get_scene_duration_seconds(frames, scene_start_frame, scene_end_frame):
    """Estimate scene duration in seconds from frame timestamps."""
    # Check if field exists in structured array dtype
    dtype_names = frames.dtype.names if hasattr(frames.dtype, 'names') and frames.dtype.names else None
    if dtype_names is None or 'timestamp' not in dtype_names:
        return None
    
    timestamps = frames['timestamp']
    
    if scene_start_frame >= len(timestamps) or scene_end_frame > len(timestamps):
        return None
    
    start_time = timestamps[scene_start_frame]
    end_time = timestamps[scene_end_frame - 1] if scene_end_frame > 0 else timestamps[scene_start_frame]
    
    # Assume timestamps are in nanoseconds
    duration_ns = end_time - start_time
    duration_seconds = duration_ns / 1e9
    
    return duration_seconds


def get_average_agent_count(frames, agents, scene_start_frame, scene_end_frame):
    """Calculate average agent count per frame in the scene."""
    # Check if field exists in structured array dtype
    dtype_names = frames.dtype.names if hasattr(frames.dtype, 'names') and frames.dtype.names else None
    if dtype_names is None or 'agent_index_interval' not in dtype_names:
        return None
    
    agent_intervals = frames['agent_index_interval']
    
    total_agents = 0
    frame_count = 0
    
    for frame_idx in range(scene_start_frame, min(scene_end_frame, len(agent_intervals))):
        start_agent, end_agent = agent_intervals[frame_idx]
        agent_count = end_agent - start_agent
        total_agents += agent_count
        frame_count += 1
    
    if frame_count == 0:
        return None
    
    return total_agents / frame_count


def main():
    """Main function to list candidate scenes."""
    # Get dataset path from environment or command line
    # Check L5KIT_DATASET_PATH first, then L5KIT_DATA_ROOT as fallback
    dataset_path = os.environ.get('L5KIT_DATASET_PATH') or os.environ.get('L5KIT_DATA_ROOT')
    
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    
    if not dataset_path:
        print("ERROR: Dataset path not provided")
        print("Usage: python list_candidate_scenes.py [dataset_path]")
        print("   or: export L5KIT_DATASET_PATH=/path/to/dataset.zarr")
        print("   or: export L5KIT_DATA_ROOT=/path/to/dataset.zarr")
        sys.exit(1)
    
    print(f"Listing candidate scenes from: {dataset_path}")
    print("=" * 80)
    
    # Load dataset
    root = load_dataset(dataset_path)
    
    if 'scenes' not in root:
        print("ERROR: 'scenes' array not found in dataset")
        sys.exit(1)
    
    if 'frames' not in root:
        print("ERROR: 'frames' array not found in dataset")
        sys.exit(1)
    
    if 'agents' not in root:
        print("ERROR: 'agents' array not found in dataset")
        sys.exit(1)
    
    scenes = root['scenes']
    frames = root['frames']
    agents = root['agents']
    
    # Check if field exists in structured array dtype
    dtype_names = scenes.dtype.names if hasattr(scenes.dtype, 'names') and scenes.dtype.names else None
    if dtype_names is None or 'frame_index_interval' not in dtype_names:
        print("ERROR: 'frame_index_interval' not found in scenes array")
        sys.exit(1)
    
    intervals = scenes['frame_index_interval']
    num_scenes = len(intervals)
    
    print(f"Total scenes: {num_scenes}")
    print()
    print(f"{'Scene':<8} {'Frames':<10} {'Duration (s)':<15} {'Avg Agents':<12}")
    print("-" * 80)
    
    for scene_idx in range(num_scenes):
        start_frame, end_frame = intervals[scene_idx]
        frame_count = end_frame - start_frame
        
        # Get duration
        duration = get_scene_duration_seconds(frames, start_frame, end_frame)
        duration_str = f"{duration:.2f}" if duration else "N/A"
        
        # Get average agent count
        avg_agents = get_average_agent_count(frames, agents, start_frame, end_frame)
        avg_agents_str = f"{avg_agents:.1f}" if avg_agents else "N/A"
        
        print(f"{scene_idx:<8} {frame_count:<10} {duration_str:<15} {avg_agents_str:<12}")
    
    print()
    print("=" * 80)
    print("Note: This is for inspection only. Golden scene selection will happen in later phases.")


if __name__ == '__main__':
    main()

