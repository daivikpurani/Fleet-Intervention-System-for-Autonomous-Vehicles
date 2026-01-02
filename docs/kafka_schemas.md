# Kafka Schemas

## Topics

### raw_telemetry

**Purpose**: Stream of raw vehicle telemetry events from the replay service. Each event represents a single vehicle's state at a specific frame in a scene.

**Partition Key**: `vehicle_id` (string)

**Ordering Guarantees**: 
- Events are ordered per vehicle within a partition
- Events from the same vehicle_id will always be processed in order
- Events from different vehicles may be processed out of order

**At-Least-Once Semantics**: 
- Messages are acknowledged after successful processing
- Duplicate messages may be delivered in case of failures
- Deduplication will be implemented later using `event_id`

**Out-of-Order Tolerance**: 
- Out-of-order events from the same vehicle are not expected in normal operation
- Out-of-order tolerance will be implemented in later phases using event timestamps

### anomalies

**Purpose**: Stream of detected anomalies from the anomaly service. Each event represents a single anomaly detected for a vehicle at a specific point in time.

**Partition Key**: `vehicle_id` (string)

**Ordering Guarantees**: 
- Anomalies are ordered per vehicle within a partition
- Anomalies from the same vehicle_id will be processed in order
- Anomalies from different vehicles may be processed out of order

**At-Least-Once Semantics**: 
- Messages are acknowledged after successful processing
- Duplicate messages may be delivered in case of failures
- Deduplication will be implemented later using `anomaly_id`

**Out-of-Order Tolerance**: 
- Out-of-order anomalies from the same vehicle are not expected in normal operation
- Out-of-order tolerance will be implemented in later phases using event timestamps

**Threshold Calibration**: 
- Anomaly detection thresholds are calibrated from golden scenes using robust statistics (percentiles)
- Thresholds are computed from the sample.zarr dataset and stored in `services/anomaly-service/config/thresholds.json`
- Each `AnomalyEvent` includes the threshold values used in detection for explainability

### operator_actions

**Purpose**: Stream of operator actions (e.g., dispatch, acknowledge, escalate) from the operator service. Each event represents a single action taken by an operator.

**Partition Key**: `action_id` (string)

**Ordering Guarantees**: 
- Actions are distributed across partitions based on action_id
- No ordering guarantees between different actions
- Each action is uniquely identified by its action_id

**At-Least-Once Semantics**: 
- Messages are acknowledged after successful processing
- Duplicate messages may be delivered in case of failures
- Deduplication will be implemented later using `action_id`

**Out-of-Order Tolerance**: 
- Out-of-order actions from the same vehicle are not expected in normal operation
- Out-of-order tolerance will be implemented in later phases using event timestamps

## Important Notes

**There is NO operator_alerts topic**: Alerts are persisted directly to Postgres in later phases. The operator service reads anomalies from the `anomalies` topic and creates alerts in the database.

## Message Formats

See `services/schemas/events.py` for Pydantic model definitions:
- `RawTelemetryEvent`
- `AnomalyEvent`
- `OperatorActionEvent`

## Partitioning Strategy

- `raw_telemetry` and `anomalies` topics use `vehicle_id` as the partition key to ensure:
  - Per-vehicle ordering guarantees
  - Efficient processing of vehicle-specific operations
  - Natural load distribution across partitions
- `operator_actions` topic uses `action_id` as the partition key to ensure:
  - Unique distribution of actions across partitions
  - No ordering dependencies between actions
