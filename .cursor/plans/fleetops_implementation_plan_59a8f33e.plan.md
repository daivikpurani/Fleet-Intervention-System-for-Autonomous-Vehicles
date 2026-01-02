---
name: FleetOps Implementation Plan
overview: Complete step-by-step implementation plan for FleetOps - an autonomous fleet response system that replays L5Kit dataset telemetry, detects anomalies via Kafka streaming, and visualizes them in a React + MapboxGL operator dashboard. The plan covers repository structure, Kafka design, dataset replay, anomaly detection, FastAPI services, Postgres schema, React UI, and a deterministic demo script.
todos: []
---

# FleetOps

– Autonomous Fleet Response System

## Implementation Plan

### Architecture Overview

```javascript
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│ L5Kit       │────▶│ replay-      │────▶│ Kafka       │────▶│ anomaly-    │
│ Dataset     │     │ service      │     │ (Docker)    │     │ service     │
│ (zarr)      │     │              │     │             │     │             │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
                                                                    │
                                                                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│ React +     │◀────│ operator-    │◀────│ Postgres    │◀────│ anomaly-    │
│ MapboxGL    │     │ service      │     │ (Docker)    │     │ service     │
│ Dashboard   │     │ (WebSocket)  │     │             │     │             │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

---

## Phase 1: Repository Layout & Project Structure

### Goal

Establish the complete folder structure with clear service boundaries.

### Folder Structure

```javascript
FleetOps/
├── README.md
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
│
├── services/
│   ├── replay-service/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Settings (Kafka, dataset paths)
│   │   ├── dataset/
│   │   │   ├── __init__.py
│   │   │   ├── reader.py           # L5Kit zarr reader
│   │   │   ├── normalizer.py       # Telemetry normalization
│   │   │   └── golden_scenes.py    # 3 fixed scene definitions
│   │   ├── replay/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Deterministic replay loop
│   │   │   └── scheduler.py        # Frame timing
│   │   └── kafka_producer.py       # Kafka producer wrapper
│   │
│   ├── anomaly-service/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py
│   │   ├── kafka_consumer.py       # Consumer for raw_telemetry
│   │   ├── features/
│   │   │   ├── __init__.py
│   │   │   ├── extractors.py       # Feature computation
│   │   │   └── windows.py          # Sliding window logic
│   │   ├── anomalies/
│   │   │   ├── __init__.py
│   │   │   ├── detectors.py        # Rule-based detectors
│   │   │   ├── rules.py            # Threshold rules
│   │   │   └── severity.py         # Severity mapping
│   │   └── kafka_producer.py       # Producer for anomalies topic
│   │
│   └── operator-service/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app + WebSocket
│       ├── config.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── alerts.py            # Pydantic models
│       │   ├── vehicles.py
│       │   └── actions.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── models.py            # SQLAlchemy models
│       │   ├── session.py           # DB session factory
│       │   └── migrations/         # Alembic migrations
│       ├── kafka_consumer.py        # Consumer for anomalies topic
│       ├── api/
│       │   ├── __init__.py
│       │   ├── alerts.py            # REST endpoints
│       │   ├── vehicles.py
│       │   └── actions.py
│       └── websocket/
│           ├── __init__.py
│           └── handler.py           # WebSocket manager
│
├── ui/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── MapView.tsx         # MapboxGL map
│   │   │   ├── VehicleLayer.tsx    # Vehicle markers
│   │   │   ├── AlertList.tsx       # Alert sidebar
│   │   │   ├── VehicleDetail.tsx   # Vehicle info panel
│   │   │   ├── IncidentPanel.tsx   # Evidence viewer
│   │   │   └── ActionButtons.tsx   # Operator actions
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts     # WebSocket hook
│   │   │   └── useAlerts.ts        # Alert state
│   │   ├── services/
│   │   │   └── api.ts              # REST client
│   │   └── types/
│   │       └── index.ts            # TypeScript types
│   │
├── scripts/
│   ├── setup_dataset.sh            # Download/prepare L5Kit data
│   ├── run_demo.sh                 # Deterministic demo script
│   └── seed_golden_scenes.py       # Extract 3 scenes
│
├── tests/
│   ├── unit/
│   │   ├── test_features.py
│   │   ├── test_anomalies.py
│   │   └── test_replay.py
│   └── integration/
│       └── test_kafka_flow.py
│
└── docs/
    ├── architecture.md
    ├── kafka_schemas.md
    └── demo_script.md
```



### Definition of Done

- All folders created
- Empty `__init__.py` files in place
- `docker-compose.yml` skeleton with services defined
- `.gitignore` includes Python, Node, Docker artifacts

---

## Phase 2: Kafka Design

### Goal

Define Kafka topics, partitioning, message schemas, and deduplication strategy.

### Topics

| Topic | Partitions | Key | Purpose ||-------|-----------|-----|---------|| `raw_telemetry` | 6 | `vehicle_id` (scene_id + track_id) | Raw telemetry from replay || `anomalies` | 6 | `vehicle_id` | Detected anomalies || `operator_alerts` | 3 | `alert_id` (UUID) | Alert lifecycle events || `operator_actions` | 3 | `action_id` (UUID) | Operator action commands |

### Message Schemas

#### `raw_telemetry` Topic

```json
{
  "event_id": "uuid-v4",
  "vehicle_id": "scene_123_track_456",
  "scene_id": "scene_123",
  "track_id": 456,
  "event_time": "2024-01-15T10:23:45.123Z",  // Dataset timestamp
  "processing_time": "2024-01-15T10:23:45.125Z",  // Kafka ingestion time
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
    "yaw": 1.23,  // radians
    "yaw_rate": 0.05,
    "label_probability": 0.95,
    "track_length": 120
  },
  "metadata": {
    "replay_session_id": "session_abc123",
    "replay_rate": 10.0  // Hz
  }
}
```



#### `anomalies` Topic

```json
{
  "anomaly_id": "uuid-v4",
  "event_id": "uuid-v4",  // Links to raw_telemetry event_id
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



#### `operator_alerts` Topic

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



#### `operator_actions` Topic

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



### Partitioning Strategy

- Partition by `vehicle_id` hash to ensure per-vehicle ordering
- Use `vehicle_id` as Kafka message key
- Consumer groups: `anomaly-service-group`, `operator-service-group`

### Deduplication

- Use `event_id` as idempotency key in producers
- In-memory cache (TTL 60s) to drop duplicates
- Store `(vehicle_id, event_id)` pairs with timestamps
- For out-of-order: ring buffer per vehicle (last 10 frames), reorder if within 2-frame tolerance

### Consumer Configuration

```python
# Example config
{
    "bootstrap_servers": "localhost:9092",
    "group_id": "anomaly-service-group",
    "auto_offset_reset": "earliest",
    "enable_auto_commit": False,  # Manual commit for at-least-once
    "max_poll_records": 100,
    "session_timeout_ms": 30000
}
```



### Definition of Done

- Schema documentation in `docs/kafka_schemas.md`
- Pydantic models for all message types
- Producer/consumer wrapper classes with deduplication
- Manual verification: produce test messages, verify partitioning

---

## Phase 3: Dataset Ingestion & Replay

### Goal

Read L5Kit zarr dataset, normalize telemetry, and implement deterministic replay.

### L5Kit Dataset Structure (Standard Zarr)

```javascript
dataset.zarr/
├── scenes/          # Scene metadata
├── frames/          # Frame-level data
├── agents/          # Agent tracks
└── tl_faces/        # Traffic lights (not used)
```

Key fields:

- `scenes`: `frame_index_interval`, `host`, `start_time`, `end_time`
- `frames`: `timestamp`, `agent_index_interval`, `traffic_light_faces_index_interval`
- `agents`: `centroid` (x, y, z), `yaw`, `velocity` (x, y, z), `track_id`, `label_probabilities`

### Golden Scenes Selection

Select 3 scenes with:

- Duration ~60 seconds each
- Multiple active agents (track_ids)
- At least one scene with observable anomalies (for demo)

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



### Telemetry Normalization

Map L5Kit fields to our schema:

```python
def normalize_telemetry(frame_data, agent_data):
    return {
        "position": {
            "x": agent_data["centroid"][0],
            "y": agent_data["centroid"][1],
            "z": agent_data["centroid"][2]
        },
        "velocity": {
            "x": agent_data["velocity"][0],
            "y": agent_data["velocity"][1],
            "z": agent_data["velocity"][2],
            "magnitude": np.linalg.norm(agent_data["velocity"])
        },
        "acceleration": compute_acceleration(agent_data),  # From velocity deltas
        "yaw": agent_data["yaw"],
        "yaw_rate": compute_yaw_rate(agent_data),
        "label_probability": max(agent_data["label_probabilities"]),
        "track_length": agent_data.get("track_length", 0)
    }
```



### Replay Engine

Deterministic replay loop:

1. Load golden scenes
2. For each scene, iterate frames at fixed rate (10 Hz default)
3. For each frame, extract all active agents (track_ids)
4. Emit `raw_telemetry` message per agent per frame
5. Use `vehicle_id = f"{scene_id}_track_{track_id}"`

Replay session:

- Generate `replay_session_id` (UUID) at start
- Emit all frames for scene_001, then scene_002, then scene_003
- Maintain frame timing: `time.sleep(1.0 / replay_rate_hz)`

### Vehicle ID Abstraction

Document in code: "Each track_id in the dataset is treated as an independent fleet vehicle for monitoring purposes. This abstraction allows us to monitor multiple vehicles concurrently within a single scene."

### Definition of Done

- L5Kit zarr reader implemented
- Golden scenes extracted and stored
- Replay engine emits messages to `raw_telemetry` topic
- Manual verification: replay one scene, verify Kafka messages

---

## Phase 4: Feature Engineering & Anomaly Logic

### Goal

Implement feature extractors and rule-based anomaly detectors.

### Feature Definitions

#### 1. Sudden Deceleration

**Features:**

- `velocity_delta_ms`: Change in velocity magnitude over window (m/s)
- `acceleration_magnitude_ms2`: Current acceleration magnitude (m/s²)
- `time_window_ms`: Time window size (ms)

**Window:** Last 5 frames (500ms at 10Hz)**Rule:**

```python
if acceleration_magnitude > 3.0 m/s² AND velocity_delta < -5.0 m/s:
    severity = "WARNING" if acceleration < 5.0 else "CRITICAL"
```

**Thresholds:**

- `decel_threshold_ms2`: 3.0
- `velocity_delta_threshold_ms`: 5.0
- `critical_decel_threshold_ms2`: 5.0

#### 2. Perception Instability

**Features:**

- `label_probability_delta`: Change in max label probability
- `position_jump_distance`: Euclidean distance of position jump (m)
- `yaw_jump_rad`: Absolute change in yaw (radians)

**Window:** Last 3 frames (300ms)**Rule:**

```python
if (label_probability_delta < -0.2 OR 
    position_jump_distance > 2.0 OR 
    yaw_jump_rad > 0.5):
    severity = "WARNING"
```

**Thresholds:**

- `label_prob_delta_threshold`: 0.2
- `position_jump_threshold_m`: 2.0
- `yaw_jump_threshold_rad`: 0.5

#### 3. Dropout Proxy

**Features:**

- `frames_since_last_update`: Count of frames without update
- `active_agent_count`: Number of active agents in current frame
- `active_agent_count_delta`: Change in active agent count

**Window:** Last 10 frames (1 second)**Rule:**

```python
if frames_since_last_update > 3:
    severity = "INFO"
if active_agent_count_delta < -5:  # Sudden drop
    severity = "WARNING"
```

**Thresholds:**

- `dropout_frame_threshold`: 3
- `agent_count_drop_threshold`: 5

### Feature Extraction Implementation

```python
class FeatureExtractor:
    def __init__(self, window_size=10):
        self.window_size = window_size
        self.ring_buffers = {}  # vehicle_id -> deque
    
    def update(self, vehicle_id, telemetry):
        # Add to ring buffer
        # Compute features from window
        pass
    
    def extract_velocity_features(self, vehicle_id):
        # Compute velocity_delta, acceleration
        pass
    
    def extract_perception_features(self, vehicle_id):
        # Compute label_prob_delta, position_jump, yaw_jump
        pass
    
    def extract_dropout_features(self, vehicle_id, current_frame_agents):
        # Compute dropout metrics
        pass
```



### Anomaly Detector

```python
class AnomalyDetector:
    def __init__(self):
        self.rules = [
            SuddenDecelerationRule(),
            PerceptionInstabilityRule(),
            DropoutProxyRule()
        ]
    
    def detect(self, vehicle_id, features):
        anomalies = []
        for rule in self.rules:
            result = rule.evaluate(features)
            if result.triggered:
                anomalies.append(result)
        return anomalies
```



### Severity Mapping

- `INFO`: Dropout proxy, minor perception glitches
- `WARNING`: Sudden deceleration (moderate), perception instability
- `CRITICAL`: Sudden deceleration (severe), multiple concurrent anomalies

### Definition of Done

- Feature extractors implemented with ring buffers
- All 3 anomaly rules implemented
- Anomalies emitted to `anomalies` topic
- Manual verification: inject test telemetry, verify anomaly detection

---

## Phase 5: Service APIs

### Goal

Implement FastAPI services with REST endpoints and WebSocket support.

### replay-service API

**Responsibilities:**

- Start/stop replay sessions
- Query replay status
- List golden scenes

**Endpoints:**

```javascript
POST   /replay/start
  Body: { "scene_ids": ["scene_001"], "replay_rate_hz": 10.0 }
  Response: { "session_id": "uuid", "status": "started" }

POST   /replay/stop
  Body: { "session_id": "uuid" }
  Response: { "status": "stopped" }

GET    /replay/status/{session_id}
  Response: { "session_id": "uuid", "status": "running", "current_frame": 42, "vehicles_active": 5 }

GET    /replay/scenes
  Response: { "scenes": [...] }
```



### anomaly-service API

**Responsibilities:**

- Health check
- Feature/rule configuration (read-only for demo)

**Endpoints:**

```javascript
GET    /health
  Response: { "status": "healthy", "kafka_connected": true }

GET    /anomalies/rules
  Response: { "rules": [...] }
```

**Kafka Consumer:**

- Consumes `raw_telemetry` topic
- Extracts features, runs detectors
- Produces to `anomalies` topic

### operator-service API

**Responsibilities:**

- Alert management
- Vehicle state queries
- Operator actions
- WebSocket for real-time updates

**REST Endpoints:**

```javascript
GET    /alerts
  Query: ?status=OPEN&severity=WARNING&vehicle_id=...
  Response: { "alerts": [...] }

GET    /alerts/{alert_id}
  Response: { "alert": {...}, "anomaly": {...}, "vehicle": {...} }

POST   /alerts/{alert_id}/acknowledge
  Body: { "operator_id": "operator_001" }
  Response: { "alert_id": "uuid", "status": "ACKNOWLEDGED" }

POST   /alerts/{alert_id}/assign
  Body: { "operator_id": "operator_001" }
  Response: { "alert_id": "uuid", "assigned_operator_id": "operator_001" }

POST   /alerts/{alert_id}/actions
  Body: { "action_type": "PULL_OVER_SIMULATED", "operator_id": "operator_001" }
  Response: { "action_id": "uuid", "status": "executed" }

GET    /vehicles
  Query: ?vehicle_id=...
  Response: { "vehicles": [...] }

GET    /vehicles/{vehicle_id}
  Response: { "vehicle": {...}, "current_alerts": [...] }

GET    /vehicles/{vehicle_id}/history
  Response: { "incidents": [...] }
```

**WebSocket:**

```javascript
WS     /ws
  Events:
    - alert_created: { "alert": {...} }
    - alert_updated: { "alert": {...} }
    - vehicle_updated: { "vehicle": {...} }
    - action_executed: { "action": {...} }
```

**Kafka Consumer:**

- Consumes `anomalies` topic
- Creates alerts in DB
- Emits WebSocket events

### Definition of Done

- All endpoints implemented with Pydantic models
- WebSocket manager with broadcast capability
- Manual verification: test endpoints with curl/Postman

---

## Phase 6: Operator State & Persistence

### Goal

Design Postgres schema and implement alert lifecycle management.

### Database Schema

#### Tables

**alerts**

```sql
CREATE TABLE alerts (
    alert_id UUID PRIMARY KEY,
    anomaly_id UUID NOT NULL,
    vehicle_id VARCHAR(255) NOT NULL,
    event_time TIMESTAMP NOT NULL,
    alert_status VARCHAR(50) NOT NULL,  -- OPEN, ACKNOWLEDGED, RESOLVED
    severity VARCHAR(50) NOT NULL,      -- INFO, WARNING, CRITICAL
    anomaly_type VARCHAR(100) NOT NULL,
    assigned_operator_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    INDEX idx_vehicle_id (vehicle_id),
    INDEX idx_status (alert_status),
    INDEX idx_severity (severity)
);
```

**vehicles**

```sql
CREATE TABLE vehicles (
    vehicle_id VARCHAR(255) PRIMARY KEY,
    scene_id VARCHAR(255) NOT NULL,
    track_id INTEGER NOT NULL,
    current_state VARCHAR(50) DEFAULT 'NORMAL',  -- NORMAL, DEGRADED, ALERTING, UNDER_INTERVENTION
    last_telemetry_time TIMESTAMP,
    last_position_x FLOAT,
    last_position_y FLOAT,
    last_velocity_magnitude FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**operator_actions**

```sql
CREATE TABLE operator_actions (
    action_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    vehicle_id VARCHAR(255) NOT NULL,
    operator_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(100) NOT NULL,  -- ACKNOWLEDGE, ASSIGN_OPERATOR, PULL_OVER_SIMULATED, etc.
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
```

**incident_history**

```sql
CREATE TABLE incident_history (
    incident_id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    vehicle_id VARCHAR(255) NOT NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    evidence JSONB,  -- Store anomaly evidence
    resolved_action_type VARCHAR(100),
    resolved_by_operator_id VARCHAR(255),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
```



### Alert Lifecycle

1. **Anomaly detected** → Create alert with status `OPEN`
2. **Operator acknowledges** → Update status to `ACKNOWLEDGED`, set `acknowledged_at`
3. **Operator takes action** → Create `operator_actions` record
4. **Action resolves issue** → Update alert status to `RESOLVED`, set `resolved_at`, create `incident_history` record

### Vehicle State Machine

- `NORMAL`: No active alerts
- `DEGRADED`: 1+ INFO/WARNING alerts, no CRITICAL
- `ALERTING`: 1+ CRITICAL alerts
- `UNDER_INTERVENTION`: Operator action in progress (e.g., `PULL_OVER_SIMULATED`)

State transitions:

- Alert created → Update vehicle state based on severity
- Action executed → Update vehicle state if needed
- Alert resolved → Recompute vehicle state from remaining alerts

### Definition of Done

- Alembic migrations created
- SQLAlchemy models defined
- Alert lifecycle logic implemented
- Manual verification: create test alerts, verify state transitions

---

## Phase 7: UI Plan

### Goal

Build React + MapboxGL dashboard for real-time monitoring.

### MapboxGL Setup

**Layers:**

1. **Base map**: Streets style
2. **Vehicle markers**: Custom markers with vehicle state colors

- Green: NORMAL
- Yellow: DEGRADED
- Orange: ALERTING
- Red: UNDER_INTERVENTION

3. **Alert markers**: Overlay on vehicles with alerts
4. **Trajectory lines**: Optional, show recent path (last 50 points)

### Components

#### MapView.tsx

- MapboxGL map container
- Manages map state, zoom, center
- Renders VehicleLayer and AlertLayer

#### VehicleLayer.tsx

- Receives vehicle positions via WebSocket
- Updates markers in real-time
- Click handler → open VehicleDetail panel

#### AlertList.tsx

- Sidebar with list of active alerts
- Filter by status, severity
- Click alert → highlight vehicle on map, show detail

#### VehicleDetail.tsx

- Panel showing:
- Vehicle ID, state
- Current position, velocity
- Active alerts
- Recent telemetry (last 10 frames)

#### IncidentPanel.tsx

- Shows anomaly evidence:
- Feature values
- Thresholds
- Triggered rule
- Timeline of events

#### ActionButtons.tsx

- Buttons for operator actions:
- Acknowledge
- Assign to me
- Pull over (simulated)
- Request remote assist
- Resume simulation

### WebSocket Integration

```typescript
// useWebSocket.ts
const ws = new WebSocket('ws://localhost:8003/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'alert_created':
      updateAlerts(data.alert);
      break;
    case 'vehicle_updated':
      updateVehicleOnMap(data.vehicle);
      break;
  }
};
```



### State Management

- React Context or Zustand for:
- Alert list
- Vehicle positions
- Selected vehicle/alert
- Operator actions

### Definition of Done

- Map renders with vehicle markers
- WebSocket updates positions in real-time
- Alert list updates live
- Operator actions trigger API calls
- Manual verification: run demo, verify UI updates

---

## Phase 8: Demo Script

### Goal

Create deterministic demo that showcases the full system.

### Demo Narrative

**Step 1: System Startup (0:00 - 0:10)**

- Start all services (Docker Compose)
- Verify Kafka topics created
- Verify Postgres connected
- Open UI dashboard (empty map)

**Step 2: Replay Start (0:10 - 0:15)**

- Start replay service: `POST /replay/start` with all 3 scenes
- Vehicles appear on map (green markers)
- Console log: "Replay started, session_id: ..."

**Step 3: Normal Operation (0:15 - 0:30)**

- Vehicles move smoothly on map
- No alerts
- Vehicle positions update every 100ms

**Step 4: First Anomaly (0:30 - 0:35)**

- Vehicle in scene_001 triggers sudden deceleration
- Alert appears in sidebar (WARNING)
- Vehicle marker turns yellow (DEGRADED)
- Map centers on affected vehicle

**Step 5: Operator Acknowledges (0:35 - 0:40)**

- Operator clicks "Acknowledge" on alert
- Alert status → ACKNOWLEDGED
- UI updates (alert badge changes)

**Step 6: Second Anomaly (0:40 - 0:45)**

- Different vehicle triggers perception instability
- Alert appears (WARNING)
- Vehicle marker turns orange (ALERTING)

**Step 7: Critical Anomaly (0:45 - 0:50)**

- Vehicle triggers severe sudden deceleration (CRITICAL)
- Alert appears (red, top of list)
- Vehicle marker turns red (UNDER_INTERVENTION)
- Incident panel shows evidence

**Step 8: Operator Intervention (0:50 - 1:00)**

- Operator clicks "Pull Over (Simulated)"
- Action executed
- Vehicle state → UNDER_INTERVENTION
- Alert status → RESOLVED after simulated delay
- Incident history created

**Step 9: Demo Complete (1:00)**

- All scenes replayed
- Summary: X alerts, Y resolved, Z incidents

### Demo Script Implementation

```bash
#!/bin/bash
# scripts/run_demo.sh

echo "Starting FleetOps Demo..."

# Start infrastructure
docker-compose up -d

# Wait for services
sleep 10

# Start replay
curl -X POST http://localhost:8001/replay/start \
  -H "Content-Type: application/json" \
  -d '{"scene_ids": ["scene_001", "scene_002", "scene_003"], "replay_rate_hz": 10.0}'

echo "Demo running. Open http://localhost:5173 to view dashboard."
echo "Press Ctrl+C to stop."

# Monitor logs
docker-compose logs -f
```



### Golden Scene Selection for Demo

Ensure scene_001 contains:

- At least one vehicle with observable sudden deceleration
- Multiple vehicles for concurrent monitoring

### Definition of Done

- Demo script runs end-to-end
- All visual states appear as expected
- Manual verification: run demo, verify each step

---

## Phase 9: Observability

### Goal

Add structured logging and basic latency tracking.

### Structured Logging

Use Python `structlog`:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "anomaly_detected",
    vehicle_id="scene_001_track_456",
    anomaly_type="sudden_deceleration",
    severity="WARNING",
    event_time="2024-01-15T10:23:45.123Z",
    processing_latency_ms=5.2
)
```



### Log Fields

- `timestamp`: ISO 8601
- `service`: `replay-service`, `anomaly-service`, `operator-service`
- `level`: `INFO`, `WARNING`, `ERROR`
- `event_type`: `telemetry_emitted`, `anomaly_detected`, `alert_created`, etc.
- Context: `vehicle_id`, `alert_id`, `session_id`, etc.

### Latency Estimation

Track:

- `replay_to_kafka_latency`: Time from replay emit to Kafka produce
- `kafka_to_anomaly_latency`: Time from Kafka consume to anomaly detection
- `anomaly_to_alert_latency`: Time from anomaly to alert creation

Store in logs, not metrics (minimal observability).

### Definition of Done

- Structured logs in all services
- Latency fields included
- Manual verification: check logs during demo

---

## Phase 10: README Structure

### Goal

Document the system with clear disclaimers and architecture overview.

### README Sections

1. **Project Overview**

- What this system models (post-perception telemetry, anomaly detection, operator workflow)
- What it intentionally does NOT model (sensor fusion, real vehicle control, production safety)

2. **Architecture**

- System diagram (mermaid)
- Service responsibilities
- Data flow

3. **Prerequisites**

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- L5Kit dataset (instructions for download)

4. **Setup**

- Clone repo
- Install dependencies
- Download/prepare dataset
- Run `docker-compose up`
- Start services
- Open UI

5. **Demo Walkthrough**

- Step-by-step demo narrative
- Expected visual states
- How to verify each component

6. **Design Tradeoffs**

- Why Kafka (streaming semantics)
- Why rule-based anomalies (explainability)
- Why vehicle_id abstraction (concurrent monitoring)
- At-least-once delivery (duplicate handling)

7. **Project Structure**

- Folder layout explanation

8. **API Documentation**

- Links to OpenAPI docs (FastAPI auto-generates)

9. **Limitations & Disclaimers**

- Not production-ready
- No safety guarantees
- Simulated interventions only
- Dataset replay is synthetic

10. **Future Enhancements** (optional)

    - ML-based anomaly detection
    - Multi-scene concurrent replay
    - Historical analysis

### Definition of Done

- README.md complete with all sections
- Architecture diagram included
- Manual verification: README is clear and complete

---

## Implementation Phases Summary

| Phase | Goal | Key Deliverables ||-------|------|-----------------|| 1 | Repository Layout | Folder structure, docker-compose skeleton || 2 | Kafka Design | Topics, schemas, deduplication || 3 | Dataset Replay | L5Kit reader, replay engine, golden scenes || 4 | Anomaly Detection | Feature extractors, rule-based detectors || 5 | Service APIs | FastAPI endpoints, WebSocket || 6 | Persistence | Postgres schema, alert lifecycle || 7 | UI Dashboard | React + MapboxGL, real-time updates || 8 | Demo Script | Deterministic demo narrative || 9 | Observability | Structured logging, latency tracking || 10 | Documentation | README with architecture and disclaimers |---

## Common Pitfalls & Solutions

1. **Kafka message ordering**: Use `vehicle_id` as key, partition by hash
2. **Out-of-order events**: Ring buffer with 2-frame tolerance
3. **Duplicate events**: Idempotency keys, in-memory cache
4. **UI performance**: Throttle WebSocket updates, use React.memo
5. **Dataset loading**: Cache zarr arrays in memory for replay
6. **State consistency**: Update vehicle state atomically with alerts

---

## Verification Checklist

After each phase:

- [ ] Code runs without errors
- [ ] Manual test of key functionality
- [ ] Logs show expected events
- [ ] No hardcoded paths (use config)
- [ ] Error handling for edge cases

Final system verification:

- [ ] Demo script runs end-to-end