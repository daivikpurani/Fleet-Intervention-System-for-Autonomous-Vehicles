"""Configuration settings for replay service."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class KafkaConfig:
    """Kafka producer configuration."""

    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    # Key serializer: vehicle_id (string)
    # Value serializer: JSON (RawTelemetryEvent)


@dataclass
class ReplayConfig:
    """Replay service configuration."""

    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    dataset_path: str = os.getenv("L5KIT_DATASET_PATH", "dataset/sample.zarr")
    replay_rate_hz: float = float(os.getenv("REPLAY_RATE_HZ", "10.0"))
    demo_scenes_path: str = os.getenv(
        "DEMO_SCENES_PATH", 
        str(Path(__file__).parent / "config" / "demo_scenes.json")
    )
    
    def load_demo_scenes(self) -> Optional[Dict[str, Any]]:
        """Load demo scenes configuration.
        
        Returns:
            Demo scenes configuration dict or None if not found
        """
        try:
            with open(self.demo_scenes_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None
    
    def get_demo_scene_ids(self) -> List[int]:
        """Get list of demo scene IDs.
        
        Returns:
            List of scene IDs configured for demos
        """
        config = self.load_demo_scenes()
        if config is None:
            return [0]  # Default to scene 0
        
        scenes = config.get("scenes", [])
        return [scene["id"] for scene in scenes if "id" in scene]

