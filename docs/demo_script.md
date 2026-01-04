# Demo Script

## Overview

This document provides a step-by-step walkthrough for demonstrating the Autonomous Fleet Response System. The demo showcases real-time anomaly detection and operator intervention workflows using deterministic replay of the L5Kit dataset.

### What's New - Demo Mode Features

- **Human-Readable IDs**: Vehicles show as `AV-SF01` (ego) or `VH-4B2F` (tracked), incidents as `INC-7K3P2`
- **Demo Pacing**: 1 Hz replay rate (1 frame/second) for better visibility during presentations
- **Professional UI**: Mission control aesthetic with fleet status bar and real-time statistics
- **Enhanced Alert Cards**: Incident numbers, severity badges, and slide-in animations

### Demo Narrative

The system monitors a fleet of autonomous vehicles in an urban environment. As vehicles navigate through traffic, the anomaly detection service identifies potential safety issues:

1. **Sudden Deceleration**: A vehicle brakes abruptly (acceleration exceeds threshold)
2. **Perception Instability**: Implausible position jumps or velocity spikes indicating sensor issues
3. **Dropout Proxy**: Sudden loss of tracked agents indicating potential sensor blindness

Operators receive real-time alerts and can acknowledge, investigate, and resolve incidents.

### Demo Duration

- **Quick Demo**: ~2 minutes (single scene, key anomalies)
- **Full Demo**: ~5-10 minutes (multiple scenes, complete operator workflow)

---

## Prerequisites

Before running the demo, ensure:

1. **Infrastructure is running**:
   ```bash
   make health
   # Should show: Postgres: healthy, Kafka: healthy
   ```

2. **Dataset is available**:
   ```bash
   ls dataset/sample.zarr
   # Should show zarr directory structure
   ```

3. **Thresholds are calibrated**:
   ```bash
   ls services/anomaly-service/config/thresholds.json
   # Should exist with calibrated values
   ```

---

## Steps

### Step 1: Start All Services

Open a terminal and run:

```bash
# Start all services (infrastructure + backend + frontend)
./scripts/start_all.sh

# Or using Makefile
make start
```

**Expected Output**:
```
Starting infrastructure...
Waiting for services to be healthy...
Infrastructure is ready!
Starting replay service on port 8000...
Starting anomaly service...
Starting operator service on port 8003...
Starting frontend on port 5173...
All services started! Press Ctrl+C to stop.
```

Wait for all services to initialize (~10-15 seconds).

### Step 2: Open the Operator Dashboard

Open a web browser and navigate to:

```
http://localhost:5173
```

**Expected UI**:
- **Header**: "FleetOps Operator Dashboard" with connection status (green "Connected")
- **Left Panel**: Alert list (initially empty)
- **Center**: Vehicle map (initially empty or showing existing vehicles)
- **Right Panel**: Vehicle detail (initially showing "No vehicle selected")

### Step 3: Start Demo Replay

In a new terminal, trigger the demo replay. Use **demo mode** for presentations (slower 1 Hz rate):

```bash
# Option A: Quick start demo mode (recommended for presentations)
curl -X POST http://localhost:8000/demo/start

# Option B: Start replay with demo mode enabled
curl -X POST http://localhost:8000/replay/start \
  -H "Content-Type: application/json" \
  -d '{"scene_ids": [0], "demo_mode": true}'

# Option C: Normal speed (10 Hz) for testing
curl -X POST http://localhost:8000/replay/start \
  -H "Content-Type: application/json" \
  -d '{"scene_ids": [0, 1, 2], "demo_mode": false}'
```

**Expected Response (Demo Mode)**:
```json
{
  "status": "started",
  "message": "Demo started with 1 scene(s) at 1 Hz",
  "scene_ids": [0],
  "demo_mode": true,
  "replay_rate_hz": 1.0
}
```

### Step 4: Observe Real-Time Updates

Watch the operator dashboard as vehicles appear and anomalies are detected:

**Timeline** (approximate, in demo mode at 1 Hz):

| Time | Event |
|------|-------|
| 0-5s | Vehicles begin appearing on map with human-readable IDs (AV-SF01) |
| 5-20s | First incidents detected (INC-XXXXX) |
| 20-60s | More incidents accumulate with slide-in animations |
| 60s+ | Continuous stream of telemetry and occasional incidents |

**What to observe**:

1. **Fleet Status Bar** (top):
   - Real-time vehicle counts (Total, AV, Nominal, Alerting)
   - Alert severity breakdown (Critical, Warning, Info)
   - Live connection status with clock

2. **Map View** (center):
   - Triangle markers for AV (ego) vehicles with heading direction
   - Circle markers for tracked vehicles
   - Color coding: Green (normal), Yellow (warning), Red (critical)
   - Glow effect on selected vehicles

3. **Alert List** (left panel):
   - Human-readable incident IDs (INC-7K3P2)
   - Vehicle display IDs (AV-SF01, VH-4B2F)
   - Slide-in animation for new alerts
   - Relative timestamps ("12s ago")
   - Quick severity stats at top

4. **Vehicle Detail** (right panel):
   - Display ID and internal ID
   - Vehicle type (Autonomous Vehicle / Tracked Vehicle)
   - Speed in km/h and heading in degrees
   - State badge with pulse animation for alerts

5. **Incident Panel** (right panel):
   - Incident ID and severity badge
   - Rule display name (e.g., "Sudden Deceleration")
   - Evidence values with units
   - Action history timeline

### Step 5: Investigate an Alert

1. **Click on a CRITICAL alert** in the alert list

2. **Observe the panels update**:
   - **Vehicle Detail**: Shows vehicle ID, state, position
   - **Incident Panel**: Shows alert details including:
     - Rule name (e.g., "sudden_deceleration")
     - Severity level
     - Feature values (e.g., acceleration: -5.2 m/s²)
     - Threshold values used

3. **Click on the vehicle marker** on the map
   - Vehicle becomes selected/highlighted
   - Detail panels update to show that vehicle's information

### Step 6: Operator Workflow - Acknowledge Alert

1. **Select a CRITICAL or WARNING alert**

2. **Click the "Acknowledge" button** in the Action Buttons panel

3. **Expected behavior**:
   - Alert status changes from "OPEN" to "ACKNOWLEDGED"
   - Alert badge color may change
   - WebSocket broadcasts the update

**API equivalent**:
```bash
# Get alert ID from the UI or API
curl -X POST http://localhost:8003/alerts/{alert_id}/ack \
  -H "Content-Type: application/json" \
  -d '{"actor": "demo_operator"}'
```

### Step 7: Operator Workflow - Resolve Alert

1. **Select an acknowledged alert**

2. **Click the "Resolve" button**

3. **Expected behavior**:
   - Alert status changes to "RESOLVED"
   - Alert may move to bottom of list or be filtered out
   - Action is recorded in history

**API equivalent**:
```bash
curl -X POST http://localhost:8003/alerts/{alert_id}/resolve \
  -H "Content-Type: application/json" \
  -d '{"actor": "demo_operator", "action_type": "RESOLVE_ALERT"}'
```

### Step 8: Enable Demo Mode (Optional)

1. **Check the "Demo Mode" checkbox** in the header

2. **Demo mode behavior**:
   - Auto-selects ego vehicle when it appears
   - Automatically highlights critical alerts
   - Useful for hands-free demonstration

### Step 9: Check Replay Status

Monitor replay progress:

```bash
curl http://localhost:8000/replay/status
```

**Expected Response**:
```json
{
  "active": true,
  "current_scene": 1,
  "current_frame": 234,
  "total_frames_emitted": 1234,
  "replay_rate_hz": 10.0
}
```

### Step 10: Stop Replay

When the demo is complete:

```bash
curl -X POST http://localhost:8000/replay/stop
```

**Expected Response**:
```json
{
  "status": "stopped",
  "message": "Replay stopped"
}
```

---

## Expected Output

### Visual States

**Initial State** (before replay):
- Empty or minimal vehicle list
- No alerts
- Map shows no vehicles

**During Replay**:
- Vehicles populate the map
- Markers move as positions update
- Alert list grows as anomalies are detected
- Vehicle markers change color based on alert severity

**After Operator Actions**:
- Acknowledged alerts show "ACKNOWLEDGED" status
- Resolved alerts show "RESOLVED" status
- Action history is recorded

### Alert Distribution (Typical)

Based on calibrated thresholds:

| Rule | Expected Frequency | Severity |
|------|-------------------|----------|
| `perception_instability` | High | Mostly WARNING |
| `sudden_deceleration` | Medium | WARNING/CRITICAL |
| `dropout_proxy` | Low | INFO |

### Console Logs

**Replay Service**:
```
2026-01-03 10:00:00 - replay - INFO - Starting replay for scenes [0, 1, 2]
2026-01-03 10:00:00 - replay - INFO - Processing scene 0, frame 0/600
2026-01-03 10:00:01 - kafka_producer - INFO - Produced 15 events to raw_telemetry
```

**Anomaly Service**:
```
2026-01-03 10:00:01 - anomaly - INFO - Anomaly detected: sudden_deceleration for vehicle scene_0_track_42 at frame 156 (severity: WARNING)
2026-01-03 10:00:02 - anomaly - INFO - Anomaly detected: perception_instability for vehicle scene_0_ego at frame 167 (severity: CRITICAL)
```

**Operator Service**:
```
2026-01-03 10:00:01 - operator - INFO - Created new alert for vehicle scene_0_track_42 (rule: sudden_deceleration)
2026-01-03 10:00:01 - websocket - INFO - Broadcasting alert_created to 1 clients
```

---

## Troubleshooting

### No Vehicles Appearing

1. Check replay service is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check replay was started:
   ```bash
   curl http://localhost:8000/replay/status
   ```

3. Check Kafka messages:
   ```bash
   docker exec fleetops-kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic raw_telemetry \
     --max-messages 5
   ```

### No Alerts Appearing

1. Check anomaly service is consuming:
   ```bash
   # Look for "Anomaly detected" in anomaly service logs
   ```

2. Check thresholds.json exists and has valid values

3. Verify anomalies are being produced:
   ```bash
   docker exec fleetops-kafka kafka-console-consumer.sh \
     --bootstrap-server localhost:9092 \
     --topic anomalies \
     --max-messages 5
   ```

### WebSocket Disconnected

1. Check operator service is running:
   ```bash
   curl http://localhost:8003/health
   ```

2. Check browser console for WebSocket errors

3. Refresh the page to reconnect

### Alerts Not Updating After Actions

1. Verify action was successful (check API response)
2. Check operator service logs for errors
3. Verify WebSocket is connected (green indicator)

---

## Demo Variations

### Quick Demo (~2 minutes)

1. Start services
2. Open dashboard
3. Start replay for scene 0 only
4. Wait for alerts
5. Acknowledge one alert
6. Resolve one alert
7. Stop replay

### Deep Dive Demo (~10 minutes)

1. Start services
2. Open dashboard
3. Explain architecture while waiting
4. Start replay for all scenes
5. Explore different anomaly types
6. Demonstrate filter by vehicle
7. Walk through complete alert lifecycle
8. Show evidence panel details
9. Discuss threshold calibration
10. Stop replay and review summary

### Technical Demo

Focus on:
- Kafka message inspection
- Database queries for alerts
- WebSocket message flow
- Threshold configuration
- API endpoint exploration

---

## Key Talking Points

### What This Demonstrates

1. **Real-time streaming**: Kafka-based telemetry processing at 10 Hz
2. **Rule-based anomaly detection**: Explainable AI with clear thresholds
3. **Operator workflow**: Alert lifecycle management (open → ack → resolve)
4. **Dataset grounding**: Thresholds calibrated from actual driving data
5. **Microservices architecture**: Independent, scalable services

### What This Does NOT Demonstrate

1. ❌ Real sensor data processing
2. ❌ ML-based perception models
3. ❌ Vehicle control/actuation
4. ❌ Production safety guarantees
5. ❌ Real autonomous vehicle operation

### Explainability Features

Each alert includes:
- **Rule name**: Which detection rule triggered
- **Feature values**: Actual measurements (e.g., acceleration = -5.2 m/s²)
- **Threshold values**: The limits that were exceeded
- **Severity mapping**: How severity was determined
