# AV Fleet Intervention and Recovery System

## Project Overview

This system models an autonomous fleet response system that replays telemetry from the Lyft L5Kit dataset, detects anomalies via Kafka streaming, and provides an operator dashboard for monitoring and intervention. The system demonstrates post-perception telemetry processing, rule-based anomaly detection, and operator workflow management.

**What this models:**
- Post-perception telemetry streaming and processing
- Real-time anomaly detection using rule-based thresholds
- Operator alert management and intervention workflows
- Vehicle state tracking and incident history
- Multi-vehicle concurrent monitoring within scenes

**What it does NOT model:**
- Sensor fusion or raw sensor data processing
- Real vehicle control or actuation
- Production safety guarantees or fail-safe mechanisms
- ML-based perception or prediction models
- Real-time sensor data ingestion

## Quick Start - Running All Services

### Recommended Workflow (Infrastructure Stays Running)

**First time setup:**
```bash
# Start infrastructure once (Postgres, Kafka, Zookeeper)
make up

# Or start everything including infrastructure
./scripts/start_all.sh
```

**Daily development (infrastructure already running):**
```bash
# Just start backend services and frontend
# The script will detect infrastructure is running and skip starting it
./scripts/start_all.sh

# Or with auto-reload (recommended for development)
./scripts/start_all.sh --reload
```

**When you're done for the day:**
- Press `Ctrl+C` to stop backend services and frontend
- Infrastructure (Postgres, Kafka) stays running
- To stop infrastructure: `make down`

### Options

- `--reload` / `-r`: Enable auto-reload for backend services (uses uvicorn --reload)
- `--infra-only`: Start only infrastructure (Postgres, Kafka)
- `--backend-only`: Start only backend services
- `--frontend-only`: Start only frontend
- `--help` / `-h`: Show help message

### Services

- **Infrastructure** (stays running): Postgres (port 5432), Kafka (port 9092)
- **Backend**: replay-service (port 8000), anomaly-service (Kafka consumer), operator-service (port 8003)
- **Frontend**: Vite dev server (port 5173) with hot reload

### Why This Workflow?

- **Faster restarts**: Infrastructure takes 30-60 seconds to start; backend services start in seconds
- **Less resource usage**: Infrastructure containers stay running but idle when not in use
- **Better for development**: You can restart backend services quickly without waiting for Kafka/Postgres

## How to Run Phase 0 Checks

Phase 0 sets up the local development environment and validates the L5Kit dataset.

### Prerequisites

- Docker Desktop for Mac (Apple Silicon)
- Python 3.10+
- L5Kit Sample Dataset (see `scripts/download_dataset.md`)

### Quick Start

1. **Set up infrastructure**:
   ```bash
   cp .env.example .env
   make up
   ```

2. **Download and validate dataset**:
   - Follow instructions in `scripts/download_dataset.md`
   - Set `L5KIT_DATASET_PATH` environment variable
   - Run validation: `python scripts/inspect_l5kit.py`

3. **Inspect scenes**:
   ```bash
   python scripts/list_candidate_scenes.py
   ```

For detailed instructions, see [docs/PHASE0.md](docs/PHASE0.md).

## Troubleshooting

### Kafka Cluster ID Mismatch

If Kafka fails to start with `InconsistentClusterIdException`, this means Kafka's stored cluster ID doesn't match Zookeeper's. This is automatically detected and fixed by the startup scripts.

**Quick fix:**
```bash
make kafka-reset
```

**Check for issues:**
```bash
make kafka-check
```

For more troubleshooting information, see [docs/troubleshooting.md](docs/troubleshooting.md).

## Infrastructure Commands

- `make up` - Start infrastructure (Postgres, Kafka, Zookeeper)
- `make down` - Stop infrastructure
- `make health` - Check container health status
- `make kafka-check` - Check for Kafka cluster ID mismatch
- `make kafka-reset` - Reset Kafka and Zookeeper volumes
- `make reset` - Destroy all volumes and restart infrastructure
- `make logs` - Tail logs from all containers

