"""Deterministic replay loop.

Implements replay engine that reads frames and publishes telemetry.
Deterministic ordering:
- Scene → frame_index ascending
- Agents iterated in array order
Emit one RawTelemetryEvent per agent and ego.
"""

import logging
import sys
from pathlib import Path
import threading
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

# Ensure workspace root is in path for schemas import
# This makes the import work regardless of where the service is run from
# Path: services/replay-service/replay/engine.py -> up 3 levels -> workspace root
_workspace_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from services.schemas.events import RawTelemetryEvent
from services.id_generator import (
    generate_vehicle_display_id,
    generate_scene_display_id,
    get_vehicle_type_label,
)

from ..dataset.normalizer import TelemetryNormalizer
from ..dataset.reader import DatasetReader
from ..kafka_producer import KafkaProducer
from .scheduler import ReplayScheduler

logger = logging.getLogger(__name__)


class ReplayEngine:
    """Deterministic replay engine.
    
    Replays scenes from L5Kit dataset at fixed rate (10 Hz).
    Emits RawTelemetryEvent for each agent and ego vehicle.
    Maintains deterministic ordering:
    - Scenes processed in ascending order
    - Frames processed in ascending order within each scene
    - Agents processed in array order
    """

    def __init__(
        self,
        reader: DatasetReader,
        producer: KafkaProducer,
        scheduler: ReplayScheduler,
        normalizer: TelemetryNormalizer,
    ):
        """Initialize replay engine.
        
        Args:
            reader: Dataset reader instance
            producer: Kafka producer instance
            scheduler: Replay scheduler instance
            normalizer: Telemetry normalizer instance
        """
        self.reader = reader
        self.producer = producer
        self.scheduler = scheduler
        self.normalizer = normalizer
        
        self._running_event = threading.Event()
        self._replay_thread: Optional[threading.Thread] = None
        self._current_scene_id: Optional[int] = None
        self._current_frame_index: Optional[int] = None
        self._previous_ego_data: Optional[Dict] = None
        self._previous_frame_timestamp: Optional[int] = None
        
        logger.info("Replay engine initialized")

    def start(self, scene_ids: Optional[List[int]] = None) -> None:
        """Start replay.
        
        Args:
            scene_ids: List of scene IDs to replay. If None, replays all scenes.
        """
        if self._running_event.is_set():
            logger.warning("Replay already running")
            return
        
        if scene_ids is None:
            scene_ids = self.reader.list_scenes()
        
        if not scene_ids:
            logger.warning("No scenes to replay")
            return
        
        self._running_event.set()
        self.scheduler.start()
        
        # Reset state
        self._previous_ego_data = None
        self._previous_frame_timestamp = None
        
        # Start replay thread
        self._replay_thread = threading.Thread(
            target=self._replay_loop,
            args=(scene_ids,),
            daemon=True,
        )
        self._replay_thread.start()
        
        logger.info(f"Started replay for {len(scene_ids)} scene(s)")

    def stop(self) -> None:
        """Stop replay."""
        if not self._running_event.is_set():
            logger.warning("Replay not running")
            return
        
        self._running_event.clear()
        self.scheduler.reset()
        
        if self._replay_thread:
            self._replay_thread.join(timeout=5.0)
            if self._replay_thread.is_alive():
                logger.warning("Replay thread did not terminate within timeout")
        
        # Flush any pending Kafka messages
        self.producer.flush()
        
        logger.info("Replay stopped")

    def get_status(self) -> Dict:
        """Get current replay status.
        
        Returns:
            Dictionary with status information:
            - active: Whether replay is running
            - scene_id: Current scene ID (or None)
            - frame_index: Current frame index (or None)
            - replay_rate: Current replay rate in Hz
        """
        return {
            'active': self._running_event.is_set(),
            'scene_id': self._current_scene_id,
            'frame_index': self._current_frame_index,
            'replay_rate': self.scheduler.replay_rate_hz,
        }

    def _replay_loop(self, scene_ids: List[int]) -> None:
        """Main replay loop.
        
        Processes scenes in deterministic order:
        - Scenes in ascending order
        - Frames in ascending order within each scene
        - Agents in array order
        
        Args:
            scene_ids: List of scene IDs to replay
        """
        try:
            # Process scenes in ascending order (deterministic)
            for scene_id in sorted(scene_ids):
                if not self._running_event.is_set():
                    break
                
                self._current_scene_id = scene_id
                self._replay_scene(scene_id)
            
            # Replay complete
            self._running_event.clear()
            logger.info("Replay loop completed")
            
        except Exception as e:
            logger.error(f"Error in replay loop: {e}", exc_info=True)
            self._running_event.clear()
            raise

    def _replay_scene(self, scene_id: int) -> None:
        """Replay a single scene.
        
        Args:
            scene_id: Scene ID to replay
        """
        logger.info(f"Starting replay of scene {scene_id}")
        
        # Get frame range for this scene
        start_frame, end_frame = self.reader.get_scene_frames(scene_id)
        
        # Process frames in ascending order (deterministic)
        for frame_index in range(start_frame, end_frame):
            if not self._running_event.is_set():
                break
            
            self._current_frame_index = frame_index
            self._replay_frame(scene_id, frame_index)
            
            # Wait for next frame (maintains 10 Hz rate)
            self.scheduler.wait_for_next_frame()
        
        # Reset state between scenes
        self._previous_ego_data = None
        self._previous_frame_timestamp = None
        
        logger.info(f"Completed replay of scene {scene_id}")

    def _replay_frame(self, scene_id: int, frame_index: int) -> None:
        """Replay a single frame.
        
        Emits one RawTelemetryEvent per agent and ego.
        Batches all events for the frame, then flushes once.
        
        Args:
            scene_id: Scene ID
            frame_index: Frame index
        """
        # Get frame data
        frame_data = self.reader.get_frame_data(frame_index)
        timestamp = frame_data['timestamp']
        agents = frame_data['agents']
        
        # Get processing time (wall clock)
        processing_time = datetime.utcnow()
        
        # Convert dataset timestamp to datetime
        # L5Kit timestamps are in nanoseconds
        event_time = datetime.fromtimestamp(timestamp / 1e9)
        
        # Process ego first (if available)
        # Ego vehicle_id format: "{scene_id}_ego"
        ego_data = self.reader.get_ego_data(frame_index)
        ego_track_id = None
        if ego_data is not None:
            # Get ego track_id if available (to skip it in agent processing)
            ego_agent_data = ego_data['data']
            dtype_names_ego = ego_agent_data.dtype.names if hasattr(ego_agent_data.dtype, 'names') and ego_agent_data.dtype.names else None
            if dtype_names_ego and 'track_id' in dtype_names_ego:
                ego_track_id = int(ego_agent_data['track_id'])
            
            # Normalize ego data
            normalized_ego = self.normalizer.normalize_ego(
                ego_data,
                self._previous_ego_data,
                timestamp,
                self._previous_frame_timestamp,
            )
            
            # Generate vehicle_id for ego: "{scene_id}_ego"
            vehicle_id = f"{scene_id}_ego"
            scene_id_str = str(scene_id)
            
            # Generate human-readable display IDs
            vehicle_display_id = generate_vehicle_display_id(vehicle_id, scene_id_str)
            scene_display_id = generate_scene_display_id(scene_id_str, event_time)
            vehicle_type = get_vehicle_type_label(vehicle_id)
            
            # Create and emit ego event with telemetry data
            ego_event = RawTelemetryEvent(
                event_id=uuid4(),
                event_time=event_time,
                processing_time=processing_time,
                vehicle_id=vehicle_id,
                vehicle_display_id=vehicle_display_id,
                scene_id=scene_id_str,
                scene_display_id=scene_display_id,
                frame_index=frame_index,
                is_ego=True,
                track_id=None,
                vehicle_type=vehicle_type,
                centroid=normalized_ego['centroid'],
                velocity=normalized_ego['velocity'],
                speed=normalized_ego['speed'],
                yaw=normalized_ego.get('yaw'),
                label_probabilities=None,  # Ego doesn't have label_probabilities
            )
            self.producer.produce(ego_event)
            
            # Update previous ego data for velocity calculation
            self._previous_ego_data = normalized_ego
        
        # Process agents in array order (deterministic)
        # Agent vehicle_id format: "{scene_id}_track_{track_id}"
        dtype_names = agents.dtype.names if hasattr(agents.dtype, 'names') and agents.dtype.names else None
        if dtype_names and 'track_id' in dtype_names:
            for agent in agents:
                if not self._running_event.is_set():
                    break
                
                track_id = int(agent['track_id'])
                
                # Skip ego if it was already processed (to avoid duplicate events)
                if ego_track_id is not None and track_id == ego_track_id:
                    continue
                
                # Normalize agent data
                normalized_agent = self.normalizer.normalize_agent(agent, track_id)
                
                # Generate vehicle_id for agent: "{scene_id}_track_{track_id}"
                vehicle_id = f"{scene_id}_track_{track_id}"
                scene_id_str = str(scene_id)
                
                # Generate human-readable display IDs
                vehicle_display_id = generate_vehicle_display_id(vehicle_id, scene_id_str)
                scene_display_id = generate_scene_display_id(scene_id_str, event_time)
                vehicle_type = get_vehicle_type_label(vehicle_id)
                
                # Create and emit agent event with telemetry data
                agent_event = RawTelemetryEvent(
                    event_id=uuid4(),
                    event_time=event_time,
                    processing_time=processing_time,
                    vehicle_id=vehicle_id,
                    vehicle_display_id=vehicle_display_id,
                    scene_id=scene_id_str,
                    scene_display_id=scene_display_id,
                    frame_index=frame_index,
                    is_ego=False,
                    track_id=track_id,
                    vehicle_type=vehicle_type,
                    centroid=normalized_agent['centroid'],
                    velocity=normalized_agent['velocity'],
                    speed=normalized_agent['speed'],
                    yaw=normalized_agent.get('yaw'),
                    label_probabilities=normalized_agent.get('label_probabilities'),
                )
                self.producer.produce(agent_event)
        else:
            # Fallback: use agent index as track_id if track_id not available
            agent_start = frame_data['agent_index_interval'][0]
            for i, agent in enumerate(agents):
                if not self._running_event.is_set():
                    break
                
                track_id = agent_start + i
                
                # Normalize agent data
                normalized_agent = self.normalizer.normalize_agent(agent, track_id)
                
                # Generate vehicle_id for agent: "{scene_id}_track_{track_id}"
                vehicle_id = f"{scene_id}_track_{track_id}"
                scene_id_str = str(scene_id)
                
                # Generate human-readable display IDs
                vehicle_display_id = generate_vehicle_display_id(vehicle_id, scene_id_str)
                scene_display_id = generate_scene_display_id(scene_id_str, event_time)
                vehicle_type = get_vehicle_type_label(vehicle_id)
                
                # Create and emit agent event with telemetry data
                agent_event = RawTelemetryEvent(
                    event_id=uuid4(),
                    event_time=event_time,
                    processing_time=processing_time,
                    vehicle_id=vehicle_id,
                    vehicle_display_id=vehicle_display_id,
                    scene_id=scene_id_str,
                    scene_display_id=scene_display_id,
                    frame_index=frame_index,
                    is_ego=False,
                    track_id=track_id,
                    vehicle_type=vehicle_type,
                    centroid=normalized_agent['centroid'],
                    velocity=normalized_agent['velocity'],
                    speed=normalized_agent['speed'],
                    yaw=normalized_agent.get('yaw'),
                    label_probabilities=normalized_agent.get('label_probabilities'),
                )
                self.producer.produce(agent_event)
        
        # Flush all events for this frame (batching: flush once per frame)
        self.producer.flush()
        
        # Update previous frame timestamp for ego velocity calculation
        self._previous_frame_timestamp = timestamp
