"""Threshold configuration loader.

Loads thresholds from thresholds.json file.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default thresholds (fallback if file not found)
DEFAULT_THRESHOLDS = {
    "sudden_deceleration": {
        "warning": -3.0,
        "critical": -5.0,
    },
    "centroid_jump": {
        "warning": 5.0,
        "critical": 10.0,
    },
    "velocity_spike": {
        "warning": 10.0,
        "critical": 20.0,
    },
    "label_instability": {
        "warning": 0.3,
        "critical": 0.5,
    },
    "dropout_proxy": {
        "agent_count_drop_warning": 5,
    },
}


def load_thresholds(config_path: Optional[Path] = None) -> Dict:
    """Load thresholds from JSON file.

    Args:
        config_path: Path to thresholds.json. If None, uses default location.

    Returns:
        Dictionary of thresholds with metadata
    """
    if config_path is None:
        # Default location: services/anomaly-service/config/thresholds.json
        config_path = (
            Path(__file__).parent / "thresholds.json"
        )

    if not config_path.exists():
        logger.warning(
            f"Thresholds file not found at {config_path}, using defaults"
        )
        return {
            "dataset_id": "unknown",
            "golden_scene_ids": [],
            "generated_at": None,
            "thresholds": DEFAULT_THRESHOLDS,
        }

    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        logger.info(
            f"Loaded thresholds from {config_path} "
            f"(dataset: {data.get('dataset_id', 'unknown')}, "
            f"scenes: {data.get('golden_scene_ids', [])})"
        )

        # Log threshold values
        thresholds = data.get("thresholds", {})
        for rule_name, rule_thresholds in thresholds.items():
            logger.info(f"  {rule_name}: {rule_thresholds}")

        return data
    except Exception as e:
        logger.error(f"Failed to load thresholds from {config_path}: {e}")
        logger.warning("Using default thresholds")
        return {
            "dataset_id": "unknown",
            "golden_scene_ids": [],
            "generated_at": None,
            "thresholds": DEFAULT_THRESHOLDS,
        }

