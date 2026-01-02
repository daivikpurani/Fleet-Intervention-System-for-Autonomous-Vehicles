# Phase 0: Local Development Environment Setup

## Overview

Phase 0 establishes the foundational infrastructure and validates the L5Kit dataset. This phase does **not** include:
- FastAPI services
- Kafka producers/consumers in services
- UI code
- Any future phase implementations

## Assumptions

### Dataset Variant

**Chosen**: L5Kit Sample Dataset (mini variant)

**Rationale**:
- **Demo-reliable**: Smaller size (~1-2 GB) makes it quick to download and validate
- **Lightweight**: Suitable for local development without requiring large storage
- **Complete structure**: Contains all necessary arrays (scenes, frames, agents) for validation
- **Stable format**: Well-documented zarr structure that matches the L5Kit standard

### Machine Constraints

- **Platform**: macOS Apple Silicon (ARM64)
- **No GPU assumptions**: All validation runs on CPU
- **Docker**: Required for infrastructure (Postgres, Kafka)
- **Python**: 3.10+ required

### Dataset Structure Assumptions

Based on the L5Kit standard zarr format:
- `scenes/`: Scene metadata with `frame_index_interval`
- `frames/`: Frame data with `timestamp` (nanoseconds) and `agent_index_interval`
- `agents/`: Agent tracks with `centroid` [x, y, z], `velocity` [vx, vy, vz], `yaw`, `track_id`
- `label_probabilities`: May or may not be present depending on dataset variant

**Note**: If the actual dataset fields differ from these assumptions, discrepancies will be documented in the "Dataset Discrepancies" section below.

## Infrastructure Setup

### Prerequisites

- Docker Desktop for Mac (Apple Silicon)
- Docker Compose
- Python 3.10+ with pip

### Bringing Infrastructure Up

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Start infrastructure**:
   ```bash
   make up
   ```

   This will:
   - Start Postgres 15+ on port 5432 (configurable via `POSTGRES_PORT`)
   - Start Kafka (KRaft mode) on port 9092 (configurable via `KAFKA_PORT`)
   - Wait for services to be healthy

3. **Verify services are running**:
   ```bash
   make health
   ```

   Expected output:
   ```
   Checking container health...
   Postgres:
   healthy
   Kafka:
   healthy
   ```

### Infrastructure Commands

- `make up` - Start infrastructure
- `make down` - Stop infrastructure
- `make logs` - Tail logs from all containers
- `make psql` - Connect to Postgres database
- `make reset` - Destroy volumes and restart infrastructure
- `make health` - Check container health status

### Port Configuration

All ports are configurable via environment variables in `.env`:
- `POSTGRES_PORT`: Default 5432
- `KAFKA_PORT`: Default 9092

## Dataset Setup

### Downloading the Dataset

Follow the instructions in `scripts/download_dataset.md` to manually download the L5Kit Sample Dataset.

**Key points**:
- Download the zarr format dataset
- Extract to a known location
- Set `L5KIT_DATASET_PATH` environment variable or pass as argument to scripts

### Setting Dataset Path

```bash
export L5KIT_DATASET_PATH=/path/to/sample_scenes.zarr
```

Or add to `.env`:
```
L5KIT_DATASET_PATH=/path/to/sample_scenes.zarr
```

## Running Dataset Inspection Scripts

### 1. Validate Dataset Structure

```bash
python scripts/inspect_l5kit.py [dataset_path]
```

Or with environment variable:
```bash
export L5KIT_DATASET_PATH=/path/to/dataset.zarr
python scripts/inspect_l5kit.py
```

**What it validates**:
- ✅ `scenes`, `frames`, `agents` arrays exist
- ✅ Agent centroid is 2D [x, y] or 3D [x, y, z] (uses [x, y] for 2D position)
- ✅ Agent velocity is 2D [vx, vy] or 3D [vx, vy, vz] (uses [vx, vy] for 2D velocity)
- ✅ Frame timestamp exists and is in nanoseconds
- ✅ Label probabilities exist (if present in dataset variant)

**Expected output** (good):
```
Inspecting L5Kit dataset: /path/to/sample_scenes.zarr
============================================================
PASS: scenes array exists
PASS: frames array exists
PASS: agents array exists

Array shapes:
  scenes: (100,)
  frames: (10000,)
  agents: (50000,)

PASS: agent centroid is 3D [x, y, z] (shape: (50000, 3))
      Note: Using only [x, y] for 2D position
PASS: agent velocity is 3D [vx, vy, vz] (shape: (50000, 3))
      Note: Using only [vx, vy] for 2D velocity
PASS: frame timestamp exists and appears to be in nanoseconds
      Sample timestamp: 1234567890000000000
PASS: label_probabilities exists (shape: (50000, 11))
      Note: Not interpreting as calibrated confidence

============================================================
PASS: All required invariants validated
Dataset is ready for Phase 0 validation
```

**Exit codes**:
- `0`: All validations passed
- `1`: Validation failed or dataset error

### 2. List Candidate Scenes

```bash
python scripts/list_candidate_scenes.py [dataset_path]
```

**Purpose**: Inspect scenes for later golden scene selection (not done in Phase 0).

**Expected output**:
```
Listing candidate scenes from: /path/to/sample_scenes.zarr
================================================================================
Total scenes: 100

Scene    Frames     Duration (s)    Avg Agents  
--------------------------------------------------------------------------------
0        600        60.00           12.5        
1        550        55.00           10.2        
2        650        65.00           15.3        
...
```

## What "Good" Output Looks Like

### Infrastructure Health Check

```
Checking container health...
Postgres:
healthy
Kafka:
healthy

Container status:
NAME                 STATUS
fleetops-postgres    Up (healthy)
fleetops-kafka       Up (healthy)
```

### Dataset Inspection

All checks should show `PASS`:
- All required arrays exist
- Agent centroid/velocity dimensions are valid
- Frame timestamps are in nanoseconds
- No unexpected errors

### Scene Listing

- Should list all scenes with frame counts, durations, and average agent counts
- No errors accessing arrays
- Reasonable values (durations in seconds, positive frame counts)

## Common Failure Modes and Fixes

### Infrastructure Issues

**Problem**: Containers fail to start
- **Fix**: Check Docker Desktop is running
- **Fix**: Verify ports are not already in use: `lsof -i :5432` or `lsof -i :9092`
- **Fix**: Try `make reset` to clean up volumes

**Problem**: Kafka health check fails
- **Fix**: Wait longer (Kafka takes ~30 seconds to fully start)
- **Fix**: Check logs: `make logs`
- **Fix**: Verify KRaft mode is working: `docker exec fleetops-kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

**Problem**: Postgres connection fails
- **Fix**: Verify credentials in `.env` match docker-compose.yml
- **Fix**: Check Postgres is healthy: `make health`
- **Fix**: Try connecting manually: `make psql`

### Dataset Issues

**Problem**: `Dataset path does not exist`
- **Fix**: Verify `L5KIT_DATASET_PATH` is set correctly
- **Fix**: Check the path is absolute or relative to current directory
- **Fix**: Ensure the zarr directory exists and is readable

**Problem**: `Cannot open zarr dataset`
- **Fix**: Verify the dataset is a valid zarr format
- **Fix**: Check file permissions: `ls -la /path/to/dataset.zarr`
- **Fix**: Ensure zarr Python package is installed: `pip install zarr`

**Problem**: `agents.centroid has unexpected shape`
- **Fix**: This indicates a dataset format mismatch
- **Action**: Document the discrepancy in "Dataset Discrepancies" below
- **Action**: Update validation script to handle the actual format

**Problem**: `frame timestamp appears to be in seconds/microseconds`
- **Fix**: This is a warning, not a failure
- **Action**: Document the actual timestamp format
- **Action**: Update scripts to handle the actual format if needed

**Problem**: Missing dependencies (`zarr`, `numpy`)
- **Fix**: Install requirements: `pip install -r requirements.txt`

## Dataset Discrepancies

If the actual dataset structure differs from assumptions, document here:

### [No discrepancies found yet]

**Format**: Describe the field, expected vs actual, and impact.

Example:
- **Field**: `agents.centroid`
- **Expected**: Shape (N, 3) with [x, y, z]
- **Actual**: Shape (N, 2) with [x, y] only
- **Impact**: No impact, script handles both cases
- **Action**: None needed

## Next Steps

After Phase 0 is complete:
1. Infrastructure is running and healthy
2. Dataset is validated and ready
3. Scene inspection is complete (for reference)

**Phase 1** will begin repository layout and project structure setup.

