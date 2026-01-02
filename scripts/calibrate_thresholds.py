"""Calibrate anomaly detection thresholds from golden scenes.

Reads sample.zarr and computes robust thresholds using percentiles
from distributions of features across golden scenes.
"""

import json
import logging
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# Ensure workspace root is in path
_workspace_root = Path(__file__).resolve().parent.parent
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

# Import using importlib (Python doesn't allow hyphens in module names)
import importlib.util

_replay_service_path = _workspace_root / "services" / "replay-service"
_normalizer_path = _replay_service_path / "dataset" / "normalizer.py"
_reader_path = _replay_service_path / "dataset" / "reader.py"

spec_normalizer = importlib.util.spec_from_file_location(
    "normalizer", _normalizer_path
)
normalizer_module = importlib.util.module_from_spec(spec_normalizer)
spec_normalizer.loader.exec_module(normalizer_module)
TelemetryNormalizer = normalizer_module.TelemetryNormalizer

spec_reader = importlib.util.spec_from_file_location("reader", _reader_path)
reader_module = importlib.util.module_from_spec(spec_reader)
spec_reader.loader.exec_module(reader_module)
DatasetReader = reader_module.DatasetReader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default golden scene IDs (first 3 scenes if not specified)
# These should match the golden scenes used in replay
DEFAULT_GOLDEN_SCENE_IDS = [0, 1, 2]

# Maximum time delta for valid transitions (0.5 seconds)
MAX_DT_SECONDS = 0.5


def compute_acceleration(
    prev_speed: float,
    curr_speed: float,
    dt: float,
) -> Optional[float]:
    """Compute acceleration from speed delta and time delta.

    Args:
        prev_speed: Previous speed in m/s
        curr_speed: Current speed in m/s
        dt: Time delta in seconds

    Returns:
        Acceleration in m/s², or None if dt is invalid
    """
    if dt <= 0 or dt > MAX_DT_SECONDS:
        return None
    return (curr_speed - prev_speed) / dt


def compute_centroid_displacement(
    prev_centroid: Dict[str, float],
    curr_centroid: Dict[str, float],
) -> float:
    """Compute Euclidean distance between centroids.

    Args:
        prev_centroid: Previous centroid {x, y}
        curr_centroid: Current centroid {x, y}

    Returns:
        Displacement in meters
    """
    dx = curr_centroid["x"] - prev_centroid["x"]
    dy = curr_centroid["y"] - prev_centroid["y"]
    return math.sqrt(dx * dx + dy * dy)


def compute_velocity_delta(
    prev_velocity: Dict[str, float],
    curr_velocity: Dict[str, float],
) -> float:
    """Compute magnitude of velocity change.

    Args:
        prev_velocity: Previous velocity {vx, vy}
        curr_velocity: Current velocity {vx, vy}

    Returns:
        Velocity delta magnitude in m/s
    """
    dvx = curr_velocity["vx"] - prev_velocity["vx"]
    dvy = curr_velocity["vy"] - prev_velocity["vy"]
    return math.sqrt(dvx * dvx + dvy * dvy)


def compute_label_prob_delta(
    prev_probs: Optional[List[float]],
    curr_probs: Optional[List[float]],
) -> Optional[float]:
    """Compute change in max label probability.

    Args:
        prev_probs: Previous label probabilities
        curr_probs: Current label probabilities

    Returns:
        Change in max probability, or None if not available
    """
    if prev_probs is None or curr_probs is None:
        return None
    if len(prev_probs) == 0 or len(curr_probs) == 0:
        return None
    prev_max = max(prev_probs)
    curr_max = max(curr_probs)
    return abs(curr_max - prev_max)


def calibrate_from_scenes(
    dataset_path: str,
    scene_ids: List[int],
    output_path: Path,
) -> None:
    """Calibrate thresholds from golden scenes.

    Args:
        dataset_path: Path to sample.zarr dataset
        scene_ids: List of scene IDs to use for calibration
        output_path: Path to write thresholds.json
    """
    logger.info(f"Loading dataset from {dataset_path}")
    reader = DatasetReader(dataset_path)
    normalizer = TelemetryNormalizer()

    # Collect distributions
    accelerations = []
    centroid_displacements = []
    velocity_deltas = []
    label_prob_deltas = []
    active_agent_counts = []
    agent_count_drops = []

    # Track previous frame data per vehicle
    vehicle_prev_data: Dict[str, Dict] = {}

    # Track active agent count per (scene_id, frame_index)
    scene_frame_agent_counts: Dict[tuple[int, int], int] = {}

    logger.info(f"Processing {len(scene_ids)} scenes for calibration")

    for scene_id in scene_ids:
        logger.info(f"Processing scene {scene_id}")
        start_frame, end_frame = reader.get_scene_frames(scene_id)

        prev_frame_agent_count = None

        for frame_index in range(start_frame, end_frame):
            try:
                frame_data = reader.get_frame_data(frame_index)
                agents = frame_data["agents"]
                timestamp = frame_data["timestamp"]

                # Count active agents in this frame
                active_count = len(agents)
                scene_frame_agent_counts[(scene_id, frame_index)] = active_count
                active_agent_counts.append(active_count)

                # Compute agent count drop (compared to previous frame in same scene)
                if prev_frame_agent_count is not None:
                    drop = prev_frame_agent_count - active_count
                    if drop > 0:  # Only track drops, not increases
                        agent_count_drops.append(drop)
                prev_frame_agent_count = active_count

                # Process each agent
                dtype_names = (
                    agents.dtype.names
                    if hasattr(agents.dtype, "names") and agents.dtype.names
                    else None
                )

                if dtype_names and "track_id" in dtype_names:
                    for agent in agents:
                        track_id = int(agent["track_id"])
                        vehicle_id = f"{scene_id}_track_{track_id}"

                        # Normalize agent data
                        normalized = normalizer.normalize_agent(agent, track_id)

                        # Get previous frame data for this vehicle
                        prev_data = vehicle_prev_data.get(vehicle_id)

                        if prev_data is not None:
                            # Compute time delta
                            prev_timestamp = prev_data["timestamp"]
                            dt_ns = timestamp - prev_timestamp
                            dt_seconds = dt_ns / 1e9

                            # Compute acceleration (with safety guard)
                            if dt_seconds > 0 and dt_seconds <= MAX_DT_SECONDS:
                                accel = compute_acceleration(
                                    prev_data["speed"],
                                    normalized["speed"],
                                    dt_seconds,
                                )
                                if accel is not None:
                                    accelerations.append(accel)

                            # Compute centroid displacement
                            displacement = compute_centroid_displacement(
                                prev_data["centroid"],
                                normalized["centroid"],
                            )
                            centroid_displacements.append(displacement)

                            # Compute velocity delta
                            vel_delta = compute_velocity_delta(
                                prev_data["velocity"],
                                normalized["velocity"],
                            )
                            velocity_deltas.append(vel_delta)

                            # Compute label probability delta
                            prob_delta = compute_label_prob_delta(
                                prev_data.get("label_probabilities"),
                                normalized.get("label_probabilities"),
                            )
                            if prob_delta is not None:
                                label_prob_deltas.append(prob_delta)

                        # Update previous data
                        vehicle_prev_data[vehicle_id] = {
                            "timestamp": timestamp,
                            "speed": normalized["speed"],
                            "centroid": normalized["centroid"],
                            "velocity": normalized["velocity"],
                            "label_probabilities": normalized.get(
                                "label_probabilities"
                            ),
                        }

            except Exception as e:
                logger.warning(
                    f"Error processing frame {frame_index} in scene {scene_id}: {e}"
                )
                continue

        # Clear vehicle state between scenes
        vehicle_prev_data.clear()

    logger.info("Computing thresholds from distributions")

    # Compute thresholds using percentiles
    thresholds = {}

    # Sudden deceleration thresholds
    if accelerations:
        accel_array = np.array(accelerations)
        # Warning: 1st percentile (more negative)
        thresholds["sudden_deceleration"] = {
            "warning": float(np.percentile(accel_array, 1)),
            "critical": float(np.percentile(accel_array, 0.1)),
        }
        logger.info(
            f"Sudden deceleration: warning={thresholds['sudden_deceleration']['warning']:.2f}, "
            f"critical={thresholds['sudden_deceleration']['critical']:.2f}"
        )
    else:
        logger.warning("No acceleration data, using defaults")
        thresholds["sudden_deceleration"] = {
            "warning": -3.0,
            "critical": -5.0,
        }

    # Centroid jump thresholds
    if centroid_displacements:
        disp_array = np.array(centroid_displacements)
        thresholds["centroid_jump"] = {
            "warning": float(np.percentile(disp_array, 99)),
            "critical": float(np.percentile(disp_array, 99.9)),
        }
        logger.info(
            f"Centroid jump: warning={thresholds['centroid_jump']['warning']:.2f}, "
            f"critical={thresholds['centroid_jump']['critical']:.2f}"
        )
    else:
        logger.warning("No centroid displacement data, using defaults")
        thresholds["centroid_jump"] = {
            "warning": 5.0,
            "critical": 10.0,
        }

    # Velocity spike thresholds
    if velocity_deltas:
        vel_delta_array = np.array(velocity_deltas)
        thresholds["velocity_spike"] = {
            "warning": float(np.percentile(vel_delta_array, 99)),
            "critical": float(np.percentile(vel_delta_array, 99.9)),
        }
        logger.info(
            f"Velocity spike: warning={thresholds['velocity_spike']['warning']:.2f}, "
            f"critical={thresholds['velocity_spike']['critical']:.2f}"
        )
    else:
        logger.warning("No velocity delta data, using defaults")
        thresholds["velocity_spike"] = {
            "warning": 10.0,
            "critical": 20.0,
        }

    # Label instability thresholds
    if label_prob_deltas:
        prob_delta_array = np.array(label_prob_deltas)
        thresholds["label_instability"] = {
            "warning": float(np.percentile(prob_delta_array, 99)),
            "critical": float(np.percentile(prob_delta_array, 99.9)),
        }
        logger.info(
            f"Label instability: warning={thresholds['label_instability']['warning']:.3f}, "
            f"critical={thresholds['label_instability']['critical']:.3f}"
        )
    else:
        logger.warning("No label probability delta data, using defaults")
        thresholds["label_instability"] = {
            "warning": 0.3,
            "critical": 0.5,
        }

    # Dropout proxy thresholds
    if agent_count_drops:
        drop_array = np.array(agent_count_drops)
        # Use 99th percentile of drops, or a fixed small number
        drop_threshold = float(np.percentile(drop_array, 99))
        # Cap at reasonable value
        thresholds["dropout_proxy"] = {
            "agent_count_drop_warning": max(5, int(drop_threshold)),
        }
        logger.info(
            f"Dropout proxy: agent_count_drop_warning={thresholds['dropout_proxy']['agent_count_drop_warning']}"
        )
    else:
        logger.warning("No agent count drop data, using defaults")
        thresholds["dropout_proxy"] = {
            "agent_count_drop_warning": 5,
        }

    # Create output structure
    output_data = {
        "dataset_id": "sample.zarr",
        "golden_scene_ids": scene_ids,
        "generated_at": datetime.utcnow().isoformat(),
        "thresholds": thresholds,
    }

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"Thresholds written to {output_path}")
    logger.info(f"Processed {len(accelerations)} accelerations, {len(centroid_displacements)} displacements")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Calibrate anomaly detection thresholds from golden scenes"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset/sample.zarr",
        help="Path to sample.zarr dataset",
    )
    parser.add_argument(
        "--scenes",
        type=int,
        nargs="+",
        default=None,
        help="Scene IDs to use (default: first 3 scenes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="services/anomaly-service/config/thresholds.json",
        help="Output path for thresholds.json",
    )

    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        sys.exit(1)

    scene_ids = args.scenes if args.scenes is not None else DEFAULT_GOLDEN_SCENE_IDS
    output_path = Path(args.output)

    calibrate_from_scenes(str(dataset_path), scene_ids, output_path)


if __name__ == "__main__":
    main()

