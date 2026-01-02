#!/usr/bin/env python3
"""Compare two JSONL files for determinism.

Compares run1.jsonl and run2.jsonl to verify that replay output is deterministic.
Fields that must match: vehicle_id, scene_id, frame_index, event_time, is_ego, 
track_id, centroid, velocity, speed, yaw, label_probabilities.
Fields allowed to differ: event_id, processing_time.
"""

import json
import sys
from typing import Dict, Any, Optional, Tuple

# Fields that must be identical
REQUIRED_MATCH_FIELDS = [
    'vehicle_id',
    'scene_id',
    'frame_index',
    'event_time',
    'is_ego',
    'track_id',
    'centroid',
    'velocity',
    'speed',
    'yaw',
    'label_probabilities',
]

# Fields allowed to differ
ALLOWED_DIFF_FIELDS = [
    'event_id',
    'processing_time',
]


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize event for comparison.
    
    Removes fields that are allowed to differ and normalizes data types.
    """
    normalized = {}
    for field in REQUIRED_MATCH_FIELDS:
        if field in event:
            value = event[field]
            # Normalize None vs missing
            if value is None:
                normalized[field] = None
            else:
                normalized[field] = value
        else:
            normalized[field] = None
    return normalized


def compare_events(event1: Dict[str, Any], event2: Dict[str, Any], index: int) -> Optional[str]:
    """Compare two events.
    
    Returns:
        None if events match, error message if they differ
    """
    norm1 = normalize_event(event1)
    norm2 = normalize_event(event2)
    
    for field in REQUIRED_MATCH_FIELDS:
        val1 = norm1.get(field)
        val2 = norm2.get(field)
        
        # Handle None comparison
        if val1 is None and val2 is None:
            continue
        if val1 is None or val2 is None:
            return f"Field '{field}' differs: {val1} vs {val2}"
        
        # Handle dict comparison (centroid, velocity)
        if isinstance(val1, dict) and isinstance(val2, dict):
            if val1 != val2:
                return f"Field '{field}' differs: {val1} vs {val2}"
            continue
        
        # Handle list comparison (label_probabilities)
        if isinstance(val1, list) and isinstance(val2, list):
            if len(val1) != len(val2):
                return f"Field '{field}' length differs: {len(val1)} vs {len(val2)}"
            for i, (v1, v2) in enumerate(zip(val1, val2)):
                # Float comparison with tolerance
                if isinstance(v1, float) and isinstance(v2, float):
                    if abs(v1 - v2) > 1e-9:
                        return f"Field '{field}[{i}]' differs: {v1} vs {v2}"
                elif v1 != v2:
                    return f"Field '{field}[{i}]' differs: {v1} vs {v2}"
            continue
        
        # Handle float comparison (speed, yaw)
        if isinstance(val1, float) and isinstance(val2, float):
            if abs(val1 - val2) > 1e-9:
                return f"Field '{field}' differs: {val1} vs {val2}"
            continue
        
        # Standard comparison
        if val1 != val2:
            return f"Field '{field}' differs: {val1} vs {val2}"
    
    return None


def compare_files(file1: str, file2: str) -> Tuple[bool, Optional[str]]:
    """Compare two JSONL files.
    
    Returns:
        (is_match, error_message)
    """
    events1 = []
    events2 = []
    
    # Read file1
    try:
        with open(file1, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events1.append(json.loads(line))
    except FileNotFoundError:
        return False, f"File not found: {file1}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in {file1}: {e}"
    
    # Read file2
    try:
        with open(file2, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    events2.append(json.loads(line))
    except FileNotFoundError:
        return False, f"File not found: {file2}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in {file2}: {e}"
    
    # Check lengths
    if len(events1) != len(events2):
        return False, f"Different number of events: {len(events1)} vs {len(events2)}"
    
    if len(events1) == 0:
        return False, "No events found in files"
    
    # Compare each event
    for i, (e1, e2) in enumerate(zip(events1, events2)):
        error = compare_events(e1, e2, i)
        if error:
            return False, f"Event {i}: {error}"
    
    return True, None


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 compare_determinism.py <run1.jsonl> <run2.jsonl>")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    
    is_match, error = compare_files(file1, file2)
    
    if is_match:
        print("Determinism: PASS")
        print("All events match across runs.")
        sys.exit(0)
    else:
        print("Determinism: FAIL")
        print(f"Error: {error}")
        sys.exit(1)

