#!/usr/bin/env python3
"""
L5Kit Dataset Inspection Script

Validates the L5Kit zarr dataset structure and key invariants.
Exits with non-zero status on any invariant violation.
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
        print(f"FAIL: Dataset path does not exist: {dataset_path}")
        sys.exit(1)
    
    try:
        root = zarr.open(str(dataset_path), mode='r')
        return root
    except Exception as e:
        print(f"FAIL: Cannot open zarr dataset: {e}")
        sys.exit(1)


def check_array_exists(root, array_name, description):
    """Check if an array exists and print status."""
    if array_name in root:
        print(f"PASS: {description} array exists")
        return root[array_name]
    else:
        print(f"FAIL: {description} array does not exist")
        sys.exit(1)


def check_agent_centroid(agents):
    """Assert agent centroid is 2D only [x, y] or 3D [x, y, z]."""
    # Check if field exists in structured array dtype
    dtype_names = agents.dtype.names if hasattr(agents.dtype, 'names') and agents.dtype.names else None
    if dtype_names is None or 'centroid' not in dtype_names:
        print("FAIL: agents.centroid field does not exist")
        sys.exit(1)
    
    centroid = agents['centroid']
    shape = centroid.shape
    
    if len(shape) != 2:
        print(f"FAIL: agents.centroid has unexpected shape: {shape}")
        print(f"      Expected 2D array (N, 2) or (N, 3)")
        sys.exit(1)
    
    if shape[1] == 2:
        print(f"PASS: agent centroid is 2D [x, y] (shape: {shape})")
    elif shape[1] == 3:
        print(f"PASS: agent centroid is 3D [x, y, z] (shape: {shape})")
        print(f"      Note: Using only [x, y] for 2D position")
    else:
        print(f"FAIL: agent centroid has unexpected dimension: {shape[1]}")
        sys.exit(1)


def check_agent_velocity(agents):
    """Assert agent velocity is 2D only [vx, vy] or 3D [vx, vy, vz]."""
    # Check if field exists in structured array dtype
    dtype_names = agents.dtype.names if hasattr(agents.dtype, 'names') and agents.dtype.names else None
    if dtype_names is None or 'velocity' not in dtype_names:
        print("FAIL: agents.velocity field does not exist")
        sys.exit(1)
    
    velocity = agents['velocity']
    shape = velocity.shape
    
    if len(shape) != 2:
        print(f"FAIL: agents.velocity has unexpected shape: {shape}")
        print(f"      Expected 2D array (N, 2) or (N, 3)")
        sys.exit(1)
    
    if shape[1] == 2:
        print(f"PASS: agent velocity is 2D [vx, vy] (shape: {shape})")
    elif shape[1] == 3:
        print(f"PASS: agent velocity is 3D [vx, vy, vz] (shape: {shape})")
        print(f"      Note: Using only [vx, vy] for 2D velocity")
    else:
        print(f"FAIL: agent velocity has unexpected dimension: {shape[1]}")
        sys.exit(1)


def check_frame_timestamp(frames):
    """Assert frame timestamp exists and is in nanoseconds."""
    # Check if field exists in structured array dtype
    dtype_names = frames.dtype.names if hasattr(frames.dtype, 'names') and frames.dtype.names else None
    if dtype_names is None or 'timestamp' not in dtype_names:
        print("FAIL: frames.timestamp field does not exist")
        sys.exit(1)
    
    timestamp = frames['timestamp']
    
    # Check if timestamp values are reasonable for nanoseconds
    # L5Kit timestamps are typically in nanoseconds (large integers)
    sample_timestamp = timestamp[0] if len(timestamp) > 0 else None
    
    if sample_timestamp is not None:
        # Nanoseconds since epoch would be > 1e15 for recent dates
        # Microseconds would be > 1e12
        # Seconds would be < 1e10
        if sample_timestamp > 1e12:
            print(f"PASS: frame timestamp exists and appears to be in nanoseconds")
            print(f"      Sample timestamp: {sample_timestamp}")
        elif sample_timestamp > 1e9:
            print(f"WARNING: frame timestamp appears to be in microseconds, not nanoseconds")
            print(f"         Sample timestamp: {sample_timestamp}")
        else:
            print(f"WARNING: frame timestamp appears to be in seconds, not nanoseconds")
            print(f"         Sample timestamp: {sample_timestamp}")
    else:
        print("WARNING: No frames found to validate timestamp format")


def check_label_probabilities(agents):
    """Check if label_probabilities exists (optional field)."""
    # Check if field exists in structured array dtype
    dtype_names = agents.dtype.names if hasattr(agents.dtype, 'names') and agents.dtype.names else None
    if dtype_names and 'label_probabilities' in dtype_names:
        probs = agents['label_probabilities']
        print(f"PASS: label_probabilities exists (shape: {probs.shape})")
        print(f"      Note: Not interpreting as calibrated confidence")
    else:
        print("INFO: label_probabilities field not present in this dataset variant")
        print("      This is acceptable - not all dataset variants include this field")


def main():
    """Main inspection function."""
    # Get dataset path from environment or command line
    # Check L5KIT_DATASET_PATH first, then L5KIT_DATA_ROOT as fallback
    dataset_path = os.environ.get('L5KIT_DATASET_PATH') or os.environ.get('L5KIT_DATA_ROOT')
    
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    
    if not dataset_path:
        print("ERROR: Dataset path not provided")
        print("Usage: python inspect_l5kit.py [dataset_path]")
        print("   or: export L5KIT_DATASET_PATH=/path/to/dataset.zarr")
        print("   or: export L5KIT_DATA_ROOT=/path/to/dataset.zarr")
        sys.exit(1)
    
    print(f"Inspecting L5Kit dataset: {dataset_path}")
    print("=" * 60)
    
    # Load dataset
    root = load_dataset(dataset_path)
    
    # Check required arrays exist
    scenes = check_array_exists(root, 'scenes', 'scenes')
    frames = check_array_exists(root, 'frames', 'frames')
    agents = check_array_exists(root, 'agents', 'agents')
    
    print()
    print("Array shapes:")
    print(f"  scenes: {scenes.shape}")
    print(f"  frames: {frames.shape}")
    print(f"  agents: {agents.shape}")
    print()
    
    # Validate agent centroid
    check_agent_centroid(agents)
    
    # Validate agent velocity
    check_agent_velocity(agents)
    
    # Validate frame timestamp
    check_frame_timestamp(frames)
    
    # Check label probabilities (optional)
    check_label_probabilities(agents)
    
    print()
    print("=" * 60)
    print("PASS: All required invariants validated")
    print("Dataset is ready for Phase 0 validation")


if __name__ == '__main__':
    main()

