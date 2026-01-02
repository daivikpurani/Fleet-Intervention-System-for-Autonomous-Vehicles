# Phase 3: Dataset Ingestion & Replay

## Overview

Phase 3 implements L5Kit zarr dataset reading, telemetry normalization, and deterministic replay to Kafka. This phase does **not** include:
- Anomaly detection logic
- Operator service
- UI components
- Any future phase implementations

## Assumptions

### Dataset Format

**Chosen**: L5Kit Sample Dataset (zarr format)

**Rationale**:
- **Standard format**: Well-documented zarr structure
- **Lazy loading**: Efficient memory usage with zarr
- **Complete data**: Contains all necessary arrays (scenes, frames, agents)
- **Validated**: Dataset structure validated in Phase 0

### Replay Rate

**Chosen**: Fixed 10 Hz (100ms per frame)

**Rationale**:
- **Deterministic**: Fixed rate ensures reproducible replay
- **Realistic**: Matches typical telemetry update rates
- **Manageable**: Allows real-time processing without overwhelming consumers

### Vehicle ID Format

**Chosen**: `"{scene_id}_track_{track_id}"` for agents, `"{scene_id}_ego"` for ego

**Rationale**:
- **Unique identification**: Each vehicle has unique ID across scenes
- **Traceability**: Scene and track ID embedded in vehicle ID
- **Abstraction**: Treats each track as independent fleet vehicle

## L5Kit Dataset Structure

### Standard Zarr Format

```
dataset.zarr/
├── scenes/          # Scene metadata
├── frames/          # Frame-level data
├── agents/          # Agent tracks
└── tl_faces/        # Traffic lights (not used)
```

### Key Fields

- **scenes**: `frame_index_interval`, `host`, `start_time`, `end_time`
- **frames**: `timestamp` (nanoseconds), `agent_index_interval`, `traffic_light_faces_index_interval`
- **agents**: `centroid` (x, y, z), `yaw`, `velocity` (x, y, z), `track_id`, `label_probabilities`

**Note**: Actual dataset may have 2D centroids [x, y] instead of 3D. Normalizer handles both cases.

## Golden Scenes Selection

### Selection Criteria

Select 3 scenes with:
- Duration ~60 seconds each (600 frames at 10 Hz)
- Multiple active agents (track_ids)
- At least one scene with observable anomalies (for demo)

### Storage Format

Store in `services/replay-service/dataset/golden_scenes.py`:

```python
GOLDEN_SCENES = [
    {
        "scene_id": "scene_001",
        "zarr_scene_index": 42,
        "start_frame": 100,
        "end_frame": 700,  # ~60s at 10Hz
        "description": "Highway merge with multiple vehicles"
    },
    {
        "scene_id": "scene_002",
        "zarr_scene_index": 128,
        "start_frame": 50,
        "end_frame": 650,
        "description": "Urban intersection with traffic"
    },
    {
        "scene_id": "scene_003",
        "zarr_scene_index": 205,
        "start_frame": 200,
        "end_frame": 800,
        "description": "City street with lane changes"
    }
]
```

### Scene Selection Process

1. Run scene inspection script from Phase 0
2. Identify scenes with ~600 frames
3. Verify multiple active agents
4. Document scene characteristics
5. Store in `golden_scenes.py`

## Telemetry Normalization

### Normalization Rules

Map L5Kit fields to internal schema:

- **Position**: `centroid` [x, y, z] → `{x, y, z}` (use z=0.0 if 2D)
- **Velocity**: `velocity` [vx, vy, vz] → `{x, y, z, magnitude}` (use z=0.0 if 2D)
- **Acceleration**: Compute from velocity deltas over time
- **Yaw**: Direct mapping from `yaw` field
- **Yaw Rate**: Compute from yaw deltas over time
- **Label Probability**: `max(label_probabilities)` if available
- **Track Length**: Track length in frames (if available)

### Ego Vehicle Handling

- Ego identified by `track_id == -1` or first agent in frame
- Ego vehicle_id: `"{scene_id}_ego"`
- Ego extent: Synthetic constants (length=4.5m, width=1.8m, height=1.5m)
- Ego velocity: Derived from position deltas + timestamps

### Normalization Invariants

- **Centroid**: Must be 2D [x, y] or 3D [x, y, z] (assertion failure if violated)
- **Velocity**: Must be 2D [vx, vy] or 3D [vx, vy, vz] (assertion failure if violated)
- **Fail fast**: Raise errors on unexpected formats

## Replay Engine

### Deterministic Replay Loop

1. Load golden scenes from `golden_scenes.py`
2. For each scene (in order):
   - Get frame range from scene definition
   - For each frame (ascending order):
     - Wait for next frame time (10 Hz = 100ms)
     - Read frame data from zarr
     - Extract all active agents
     - Normalize telemetry for each agent
     - Emit `RawTelemetryEvent` to Kafka
3. Process scenes sequentially (scene_001 → scene_002 → scene_003)

### Replay Session

- Generate `replay_session_id` (UUID) at start
- Include in all telemetry events
- Maintain frame timing: `time.sleep(1.0 / replay_rate_hz)`

### Frame Processing Order

**Deterministic ordering**:
- Scenes processed in ascending order
- Frames processed in ascending order within each scene
- Agents processed in array order

### Vehicle ID Generation

- **Agents**: `vehicle_id = f"{scene_id}_track_{track_id}"`
- **Ego**: `vehicle_id = f"{scene_id}_ego"`

## Implementation Components

### Dataset Reader (`dataset/reader.py`)

- Open zarr dataset in read-only mode
- Provide methods:
  - `list_scenes()`: List all scene IDs
  - `get_scene_frames(scene_id)`: Get frame range for scene
  - `get_frame_data(frame_index)`: Get frame data
  - `get_ego_data(frame_index)`: Get ego vehicle data
- Use lazy zarr access (no preloading)

### Telemetry Normalizer (`dataset/normalizer.py`)

- Normalize agent data to internal format
- Normalize ego data (with extent constants)
- Enforce invariants (assertions for centroid/velocity dimensions)
- Compute derived fields (acceleration, yaw_rate, speed)

### Replay Scheduler (`replay/scheduler.py`)

- Maintain fixed replay rate (10 Hz)
- Use wall-clock time for timing
- Provide methods:
  - `start()`: Start scheduler
  - `wait_for_next_frame()`: Wait until next frame time
  - `reset()`: Reset scheduler

### Replay Engine (`replay/engine.py`)

- Orchestrate replay loop
- Read frames from dataset
- Normalize telemetry
- Emit events to Kafka
- Maintain deterministic ordering

### Kafka Producer (`kafka_producer.py`)

- Wrap Kafka producer
- Serialize `RawTelemetryEvent` to JSON
- Set message key to `vehicle_id`
- Handle producer errors

## FastAPI Service

### Endpoints

- `POST /replay/start`: Start replay (optionally with scene_ids)
- `POST /replay/stop`: Stop replay
- `GET /replay/status`: Get replay status
- `GET /health`: Health check

### Service Structure

- Initialize components on startup
- Run replay in background thread
- Provide status via API

## What "Good" Output Looks Like

### Dataset Reader

```bash
# Test dataset reader
python -c "
from services.replay_service.dataset.reader import DatasetReader
reader = DatasetReader('dataset/sample.zarr')
scenes = reader.list_scenes()
print(f'Found {len(scenes)} scenes')
"
```

**Expected**: No errors, scene count matches dataset.

### Telemetry Normalizer

```bash
# Test normalizer
python -c "
from services.replay_service.dataset.normalizer import TelemetryNormalizer
normalizer = TelemetryNormalizer()
# Test with sample agent data
"
```

**Expected**: No errors, normalized output matches schema.

### Replay Engine

```bash
# Start replay service
cd services/replay-service
uvicorn main:app --host 0.0.0.0 --port 8000

# In another terminal, start replay
curl -X POST http://localhost:8000/replay/start \
  -H "Content-Type: application/json" \
  -d '{"scene_ids": [0]}'

# Check status
curl http://localhost:8000/replay/status
```

**Expected**: Replay starts, status shows active, messages appear in Kafka.

### Kafka Messages

```bash
# Consume messages from raw_telemetry topic
docker exec fleetops-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic raw_telemetry \
  --from-beginning \
  --max-messages 10
```

**Expected**: JSON messages with `RawTelemetryEvent` schema, `vehicle_id` as key.

## Common Failure Modes and Fixes

### Dataset Access Issues

**Problem**: `Dataset path does not exist`
- **Fix**: Verify `L5KIT_DATASET_PATH` is set correctly
- **Fix**: Check path is absolute or relative to service directory
- **Fix**: Ensure zarr dataset is readable

**Problem**: `Cannot open zarr dataset`
- **Fix**: Verify dataset is valid zarr format
- **Fix**: Check file permissions
- **Fix**: Ensure zarr package is installed: `pip install zarr`

**Problem**: `Array not found in dataset`
- **Fix**: Verify dataset has required arrays (scenes, frames, agents)
- **Fix**: Check array names match expected (case-sensitive)
- **Fix**: Validate dataset structure with Phase 0 inspection script

### Normalization Issues

**Problem**: `Centroid must be 2D [x, y]` assertion fails
- **Fix**: Check actual dataset format (may be 3D)
- **Fix**: Update normalizer to handle actual format
- **Fix**: Document discrepancy in code comments

**Problem**: `Velocity must be 2D [vx, vy]` assertion fails
- **Fix**: Check actual dataset format (may be 3D)
- **Fix**: Update normalizer to handle actual format
- **Fix**: Document discrepancy in code comments

**Problem**: Missing fields in agent data
- **Fix**: Check which fields are actually present in dataset
- **Fix**: Make optional fields truly optional in normalizer
- **Fix**: Provide default values for missing fields

### Replay Timing Issues

**Problem**: Replay runs too fast or too slow
- **Fix**: Verify scheduler uses wall-clock time
- **Fix**: Check `replay_rate_hz` configuration
- **Fix**: Ensure `time.sleep()` is called correctly

**Problem**: Frame timing drifts over time
- **Fix**: Use actual wall-clock time, not accumulated sleep time
- **Fix**: Reset timing reference periodically
- **Fix**: Calculate sleep duration based on target time, not fixed interval

### Kafka Producer Issues

**Problem**: Messages not appearing in Kafka
- **Fix**: Verify Kafka is running: `make health`
- **Fix**: Check producer configuration (bootstrap servers)
- **Fix**: Verify topic exists: `kafka-topics.sh --list`
- **Fix**: Check producer logs for errors

**Problem**: Messages have wrong key
- **Fix**: Verify `vehicle_id` is set as message key
- **Fix**: Check key serialization
- **Fix**: Inspect messages: `kafka-console-consumer.sh --property print.key=true`

**Problem**: Serialization errors
- **Fix**: Verify Pydantic model matches JSON schema
- **Fix**: Check datetime serialization (ISO 8601)
- **Fix**: Ensure all required fields are present

### FastAPI Service Issues

**Problem**: Service fails to start
- **Fix**: Check all dependencies are installed
- **Fix**: Verify configuration is correct
- **Fix**: Check logs for startup errors

**Problem**: Replay doesn't start
- **Fix**: Verify dataset path is configured
- **Fix**: Check Kafka producer is initialized
- **Fix**: Verify replay engine is created correctly

## Verification Checklist

After Phase 3 is complete:

- [ ] L5Kit zarr reader implemented and tested
- [ ] Telemetry normalizer handles 2D and 3D data
- [ ] Golden scenes selected and stored
- [ ] Replay scheduler maintains 10 Hz rate
- [ ] Replay engine processes scenes deterministically
- [ ] Kafka producer emits messages with correct schema
- [ ] FastAPI service provides start/stop/status endpoints
- [ ] All 3 golden scenes can be replayed
- [ ] Messages appear in `raw_telemetry` topic with correct format

## Next Steps

After Phase 3 is complete:
1. Dataset can be read and normalized
2. Replay engine emits telemetry to Kafka
3. Golden scenes are ready for demo

**Phase 4** will implement feature engineering and anomaly detection logic.

