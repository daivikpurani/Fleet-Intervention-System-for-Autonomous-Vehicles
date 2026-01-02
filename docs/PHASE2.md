# Phase 2: Kafka Design

## Overview

Phase 2 defines Kafka topics, partitioning strategies, message schemas, and deduplication mechanisms. This phase does **not** include:
- Service implementations
- Actual Kafka producers/consumers in services
- Database schemas
- UI components
- Any future phase implementations

## Assumptions

### Kafka Configuration

**Chosen**: Kafka in KRaft mode (no Zookeeper)

**Rationale**:
- **Simpler setup**: Fewer components to manage
- **Modern approach**: KRaft is the future of Kafka
- **Local development**: Suitable for single-node development
- **Production-ready**: Can scale to multi-node if needed

### Message Delivery Semantics

**Chosen**: At-least-once delivery

**Rationale**:
- **Reliability**: Ensures no messages are lost
- **Duplicate handling**: Consumers must handle duplicates
- **Simplicity**: Easier to reason about than exactly-once
- **Performance**: Better throughput than exactly-once

### Partitioning Strategy

**Chosen**: Partition by `vehicle_id` hash

**Rationale**:
- **Ordering guarantee**: All messages for a vehicle stay in order
- **Parallelism**: Multiple vehicles can be processed in parallel
- **Load balancing**: Even distribution across partitions

## Topics Design

### Topic Definitions

| Topic | Partitions | Key | Purpose |
|-------|-----------|-----|---------|
| `raw_telemetry` | 6 | `vehicle_id` (scene_id + track_id) | Raw telemetry from replay |
| `anomalies` | 6 | `vehicle_id` | Detected anomalies |
| `operator_alerts` | 3 | `alert_id` (UUID) | Alert lifecycle events |
| `operator_actions` | 3 | `action_id` (UUID) | Operator action commands |

### Partition Count Rationale

- **raw_telemetry** (6 partitions): High throughput, many vehicles
- **anomalies** (6 partitions): Matches raw_telemetry for parallel processing
- **operator_alerts** (3 partitions): Lower throughput, alert management
- **operator_actions** (3 partitions): Lower throughput, operator commands

## Message Schemas

### `raw_telemetry` Topic

**Purpose**: Raw telemetry events from dataset replay

**Schema**:
```json
{
  "event_id": "uuid-v4",
  "vehicle_id": "scene_123_track_456",
  "scene_id": "scene_123",
  "track_id": 456,
  "event_time": "2024-01-15T10:23:45.123Z",
  "processing_time": "2024-01-15T10:23:45.125Z",
  "frame_index": 42,
  "telemetry": {
    "position": {
      "x": 123.45,
      "y": 67.89,
      "z": 0.0
    },
    "velocity": {
      "x": 5.2,
      "y": 0.1,
      "z": 0.0,
      "magnitude": 5.2
    },
    "acceleration": {
      "x": -0.5,
      "y": 0.0,
      "z": 0.0,
      "magnitude": 0.5
    },
    "yaw": 1.23,
    "yaw_rate": 0.05,
    "label_probability": 0.95,
    "track_length": 120
  },
  "metadata": {
    "replay_session_id": "session_abc123",
    "replay_rate": 10.0
  }
}
```

**Key Fields**:
- `event_id`: Unique identifier for deduplication
- `vehicle_id`: Format: `"{scene_id}_track_{track_id}"` or `"{scene_id}_ego"`
- `event_time`: Dataset timestamp (nanoseconds converted to ISO 8601)
- `processing_time`: Kafka ingestion timestamp
- `frame_index`: Frame index in dataset

### `anomalies` Topic

**Purpose**: Detected anomalies from telemetry analysis

**Schema**:
```json
{
  "anomaly_id": "uuid-v4",
  "event_id": "uuid-v4",
  "vehicle_id": "scene_123_track_456",
  "event_time": "2024-01-15T10:23:45.123Z",
  "processing_time": "2024-01-15T10:23:45.130Z",
  "anomaly_type": "sudden_deceleration",
  "severity": "WARNING",
  "triggered_rule": "decel_threshold_exceeded",
  "features": {
    "velocity_delta": -8.5,
    "acceleration_magnitude": 4.2,
    "time_window_ms": 500
  },
  "thresholds": {
    "decel_threshold_ms2": 3.0,
    "velocity_delta_threshold_ms": 5.0
  },
  "evidence": {
    "frame_indices": [40, 41, 42],
    "velocity_history": [13.5, 10.2, 5.0],
    "acceleration_history": [-0.1, -2.5, -4.2]
  }
}
```

**Key Fields**:
- `anomaly_id`: Unique identifier for this anomaly
- `event_id`: Links back to source `raw_telemetry` event
- `anomaly_type`: Type of anomaly (e.g., "sudden_deceleration", "perception_instability")
- `severity`: INFO, WARNING, or CRITICAL
- `evidence`: Historical data supporting the anomaly

### `operator_alerts` Topic

**Purpose**: Alert lifecycle events for operator dashboard

**Schema**:
```json
{
  "alert_id": "uuid-v4",
  "anomaly_id": "uuid-v4",
  "vehicle_id": "scene_123_track_456",
  "event_time": "2024-01-15T10:23:45.123Z",
  "processing_time": "2024-01-15T10:23:45.135Z",
  "alert_status": "OPEN",
  "severity": "WARNING",
  "anomaly_type": "sudden_deceleration",
  "assigned_operator_id": null,
  "created_at": "2024-01-15T10:23:45.135Z"
}
```

**Key Fields**:
- `alert_id`: Unique identifier for the alert
- `alert_status`: OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED
- `assigned_operator_id`: Operator handling the alert (null if unassigned)

### `operator_actions` Topic

**Purpose**: Operator action commands

**Schema**:
```json
{
  "action_id": "uuid-v4",
  "alert_id": "uuid-v4",
  "vehicle_id": "scene_123_track_456",
  "operator_id": "operator_001",
  "action_type": "ACKNOWLEDGE",
  "processing_time": "2024-01-15T10:23:50.200Z",
  "metadata": {
    "comment": "Investigating anomaly"
  }
}
```

**Key Fields**:
- `action_id`: Unique identifier for the action
- `action_type`: ACKNOWLEDGE, RESOLVE, DISMISS, INTERVENE
- `operator_id`: Operator performing the action

## Partitioning Strategy

### Key Selection

- **raw_telemetry**: Use `vehicle_id` as message key
- **anomalies**: Use `vehicle_id` as message key
- **operator_alerts**: Use `alert_id` as message key
- **operator_actions**: Use `action_id` as message key

### Partition Assignment

Kafka automatically assigns partitions based on key hash:
- Same `vehicle_id` → same partition → ordering guaranteed
- Different `vehicle_id` → potentially different partition → parallel processing

### Consumer Groups

- **anomaly-service-group**: Consumes from `raw_telemetry` topic
- **operator-service-group**: Consumes from `anomalies` topic

## Deduplication Strategy

### Producer-Side Deduplication

- Use `event_id` as idempotency key
- Kafka producer idempotence enabled (if supported)
- In-memory cache (TTL 60s) to drop duplicates before sending

### Consumer-Side Deduplication

- In-memory cache: `(vehicle_id, event_id)` pairs with timestamps
- TTL: 60 seconds
- Drop messages with duplicate `(vehicle_id, event_id)` within TTL window

### Out-of-Order Handling

- Ring buffer per vehicle (last 10 frames)
- Reorder if within 2-frame tolerance
- Drop messages outside tolerance window

## Consumer Configuration

### Standard Configuration

```python
{
    "bootstrap_servers": "localhost:9092",
    "group_id": "anomaly-service-group",
    "auto_offset_reset": "earliest",
    "enable_auto_commit": False,  # Manual commit for at-least-once
    "max_poll_records": 100,
    "session_timeout_ms": 30000,
    "heartbeat_interval_ms": 10000
}
```

### Key Settings

- **auto_offset_reset**: "earliest" to process all messages from start
- **enable_auto_commit**: False for manual commit control
- **max_poll_records**: 100 for batch processing efficiency
- **session_timeout_ms**: 30000 (30 seconds) for rebalancing

## Schema Documentation

### Creating Schema Documentation

Create `docs/kafka_schemas.md` with:
- Topic definitions
- Message schemas (JSON examples)
- Field descriptions
- Partitioning strategy
- Consumer group assignments

### Pydantic Models

Create Pydantic models in `services/schemas/events.py`:
- `RawTelemetryEvent`
- `AnomalyEvent`
- `OperatorAlertEvent`
- `OperatorActionEvent`

## What "Good" Output Looks Like

### Schema Documentation

```bash
# Verify schema documentation exists
cat docs/kafka_schemas.md
```

**Expected**: Complete documentation with all topics, schemas, and strategies.

### Pydantic Models

```bash
# Verify Pydantic models exist
python -c "from services.schemas.events import RawTelemetryEvent; print('OK')"
```

**Expected**: No import errors, models are defined.

### Topic Creation (Manual Verification)

```bash
# Create topics manually for testing
docker exec fleetops-kafka kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic raw_telemetry \
  --partitions 6 \
  --replication-factor 1

docker exec fleetops-kafka kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic anomalies \
  --partitions 6 \
  --replication-factor 1

docker exec fleetops-kafka kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic operator_alerts \
  --partitions 3 \
  --replication-factor 1

docker exec fleetops-kafka kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic operator_actions \
  --partitions 3 \
  --replication-factor 1

# List topics
docker exec fleetops-kafka kafka-topics.sh --list \
  --bootstrap-server localhost:9092
```

**Expected**: All topics created with correct partition counts.

## Common Failure Modes and Fixes

### Kafka Connection Issues

**Problem**: Cannot connect to Kafka broker
- **Fix**: Verify Kafka is running: `make health`
- **Fix**: Check port configuration: `echo $KAFKA_PORT`
- **Fix**: Verify network connectivity: `docker exec fleetops-kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

**Problem**: Topic creation fails
- **Fix**: Verify Kafka is fully started (wait ~30 seconds)
- **Fix**: Check KRaft mode is working
- **Fix**: Verify bootstrap server address is correct

### Schema Validation Issues

**Problem**: Pydantic model validation fails
- **Fix**: Verify field types match JSON schema
- **Fix**: Check required vs optional fields
- **Fix**: Validate datetime formats (ISO 8601)

**Problem**: Import errors for schemas
- **Fix**: Verify `services/schemas/__init__.py` exists
- **Fix**: Check Python path includes project root
- **Fix**: Ensure dependencies are installed: `pip install pydantic`

### Partitioning Issues

**Problem**: Messages not distributed evenly
- **Fix**: Verify key is set correctly in producer
- **Fix**: Check partition count matches expected
- **Fix**: Use `kafka-console-consumer` to inspect partitions

**Problem**: Ordering not maintained
- **Fix**: Verify same `vehicle_id` goes to same partition
- **Fix**: Check consumer is processing one partition at a time
- **Fix**: Ensure max_poll_records allows sequential processing

### Deduplication Issues

**Problem**: Duplicate messages not detected
- **Fix**: Verify `event_id` is unique and consistent
- **Fix**: Check TTL cache is working correctly
- **Fix**: Ensure cache is checked before processing

## Verification Checklist

After Phase 2 is complete:

- [ ] Schema documentation in `docs/kafka_schemas.md`
- [ ] Pydantic models for all message types
- [ ] Topics can be created manually (or via script)
- [ ] Producer wrapper class structure defined
- [ ] Consumer wrapper class structure defined
- [ ] Deduplication strategy documented
- [ ] Partitioning strategy documented
- [ ] Consumer configuration documented

## Next Steps

After Phase 2 is complete:
1. Kafka topics are designed and documented
2. Message schemas are defined
3. Partitioning and deduplication strategies are established

**Phase 3** will implement dataset ingestion and replay to Kafka.

