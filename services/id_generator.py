"""Human-readable ID generation utilities for the Fleet Response System.

Provides consistent, demo-friendly identifiers for:
- Vehicles: AV-SF01 (ego) or VH-4B2F (tracked)
- Alerts/Incidents: INC-7K3P2
- Scenes: RUN-0104-A
"""

import hashlib
from datetime import datetime
from typing import Optional


# Character set for readable IDs (no ambiguous chars like 0/O, 1/I/l)
READABLE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _hash_to_readable(input_str: str, length: int = 4) -> str:
    """Convert a string to a readable hash of specified length.
    
    Args:
        input_str: Input string to hash
        length: Desired output length
        
    Returns:
        Readable alphanumeric string
    """
    # Use MD5 for consistent hashing (not for security)
    hash_bytes = hashlib.md5(input_str.encode()).digest()
    result = []
    for i in range(length):
        idx = hash_bytes[i % len(hash_bytes)] % len(READABLE_CHARS)
        result.append(READABLE_CHARS[idx])
    return "".join(result)


def generate_vehicle_display_id(vehicle_id: str, scene_id: str) -> str:
    """Generate a human-readable vehicle display ID.
    
    Ego vehicles: AV-{zone}{seq} (e.g., AV-SF01)
    Tracked vehicles: VH-{4 char hash} (e.g., VH-4B2F)
    
    Args:
        vehicle_id: Internal vehicle ID (e.g., "0_ego" or "0_track_123")
        scene_id: Scene identifier
        
    Returns:
        Human-readable display ID
    """
    if "_ego" in vehicle_id:
        # Ego vehicle: AV-SF{scene_num + 1, zero-padded}
        try:
            scene_num = int(scene_id) if scene_id.isdigit() else 0
        except (ValueError, AttributeError):
            scene_num = 0
        return f"AV-SF{scene_num + 1:02d}"
    else:
        # Tracked vehicle: VH-{hash of vehicle_id}
        hash_part = _hash_to_readable(vehicle_id, 4)
        return f"VH-{hash_part}"


def generate_incident_id(anomaly_id: str) -> str:
    """Generate a human-readable incident ID from an anomaly UUID.
    
    Format: INC-{5 char hash} (e.g., INC-7K3P2)
    
    Args:
        anomaly_id: UUID string of the anomaly
        
    Returns:
        Human-readable incident ID
    """
    # Convert UUID to readable 5-char code
    hash_part = _hash_to_readable(str(anomaly_id), 5)
    return f"INC-{hash_part}"


def generate_scene_display_id(scene_id: str, timestamp: Optional[datetime] = None) -> str:
    """Generate a human-readable scene/run ID.
    
    Format: RUN-{MMDD}-{letter} (e.g., RUN-0104-A)
    
    Args:
        scene_id: Internal scene ID
        timestamp: Optional timestamp (defaults to now)
        
    Returns:
        Human-readable run ID
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    date_part = timestamp.strftime("%m%d")
    
    # Convert scene_id to letter (0=A, 1=B, etc.)
    try:
        scene_num = int(scene_id) if scene_id.isdigit() else 0
    except (ValueError, AttributeError):
        scene_num = 0
    
    letter = chr(ord('A') + (scene_num % 26))
    
    return f"RUN-{date_part}-{letter}"


def get_vehicle_type_label(vehicle_id: str) -> str:
    """Get a human-readable type label for the vehicle.
    
    Args:
        vehicle_id: Internal vehicle ID
        
    Returns:
        Type label (e.g., "Autonomous Vehicle" or "Tracked Vehicle")
    """
    if "_ego" in vehicle_id:
        return "Autonomous Vehicle"
    return "Tracked Vehicle"


def get_short_vehicle_type(vehicle_id: str) -> str:
    """Get a short type code for the vehicle.
    
    Args:
        vehicle_id: Internal vehicle ID
        
    Returns:
        Short type code (e.g., "EGO" or "TRK")
    """
    if "_ego" in vehicle_id:
        return "EGO"
    return "TRK"


# Counter for incident IDs (used when we need sequential IDs)
_incident_counter = 0


def generate_sequential_incident_id() -> str:
    """Generate a sequential incident ID.
    
    Format: INC-{5 digit number} (e.g., INC-00042)
    
    Returns:
        Sequential incident ID
    """
    global _incident_counter
    _incident_counter += 1
    return f"INC-{_incident_counter:05d}"


def reset_incident_counter():
    """Reset the incident counter (useful for demo restarts)."""
    global _incident_counter
    _incident_counter = 0

