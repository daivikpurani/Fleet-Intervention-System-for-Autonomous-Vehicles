# Autonomous Fleet Response System

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

