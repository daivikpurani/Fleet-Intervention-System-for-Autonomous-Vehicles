# Phase 1: Repository Layout & Project Structure

## Overview

Phase 1 establishes the complete folder structure with clear service boundaries. This phase does **not** include:
- Implementation of service logic
- Kafka producers/consumers
- Database schemas
- UI components
- Any future phase implementations

## Assumptions

### Service Architecture

**Chosen**: Microservices architecture with three main services

**Rationale**:
- **Clear separation**: Each service has a single responsibility
- **Independent scaling**: Services can be scaled independently
- **Technology flexibility**: Each service can use appropriate tech stack
- **Development isolation**: Teams can work on services independently

### Service Boundaries

- **replay-service**: Handles L5Kit dataset reading and replay to Kafka
- **anomaly-service**: Consumes raw telemetry and detects anomalies
- **operator-service**: Manages alerts, provides REST API and WebSocket for UI

### Technology Stack

- **Backend**: Python 3.10+ with FastAPI
- **Frontend**: React + TypeScript + Vite
- **Infrastructure**: Docker Compose (Postgres, Kafka)
- **Database**: Postgres 15+ (for operator-service)
- **Message Queue**: Kafka (KRaft mode)

## Folder Structure Setup

### Root Level Files

1. **README.md**: Project overview and quick start
2. **.gitignore**: Python, Node, Docker artifacts
3. **docker-compose.yml**: Infrastructure services (Postgres, Kafka)
4. **requirements.txt**: Python dependencies
5. **pyproject.toml**: Python project configuration (optional)

### Services Directory

Create the following structure:

```
services/
├── replay-service/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings (Kafka, dataset paths)
│   ├── dataset/
│   │   ├── __init__.py
│   │   ├── reader.py           # L5Kit zarr reader
│   │   ├── normalizer.py       # Telemetry normalization
│   │   └── golden_scenes.py    # 3 fixed scene definitions
│   ├── replay/
│   │   ├── __init__.py
│   │   ├── engine.py           # Deterministic replay loop
│   │   └── scheduler.py        # Frame timing
│   └── kafka_producer.py       # Kafka producer wrapper
│
├── anomaly-service/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py
│   ├── kafka_consumer.py       # Consumer for raw_telemetry
│   ├── features/
│   │   ├── __init__.py
│   │   ├── extractors.py       # Feature computation
│   │   └── windows.py          # Sliding window logic
│   ├── anomalies/
│   │   ├── __init__.py
│   │   ├── detectors.py        # Rule-based detectors
│   │   ├── rules.py            # Threshold rules
│   │   └── severity.py         # Severity mapping
│   └── kafka_producer.py       # Producer for anomalies topic
│
└── operator-service/
    ├── __init__.py
    ├── main.py                 # FastAPI app + WebSocket
    ├── config.py
    ├── models/
    │   ├── __init__.py
    │   ├── alerts.py            # Pydantic models
    │   ├── vehicles.py
    │   └── actions.py
    ├── db/
    │   ├── __init__.py
    │   ├── models.py            # SQLAlchemy models
    │   ├── session.py           # DB session factory
    │   └── migrations/         # Alembic migrations
    ├── kafka_consumer.py        # Consumer for anomalies topic
    ├── api/
    │   ├── __init__.py
    │   ├── alerts.py            # REST endpoints
    │   ├── vehicles.py
    │   └── actions.py
    └── websocket/
        ├── __init__.py
        └── handler.py           # WebSocket manager
```

### UI Directory

Create the following structure:

```
ui/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── MapView.tsx         # MapboxGL map
│   │   ├── VehicleLayer.tsx    # Vehicle markers
│   │   ├── AlertList.tsx       # Alert sidebar
│   │   ├── VehicleDetail.tsx   # Vehicle info panel
│   │   ├── IncidentPanel.tsx   # Evidence viewer
│   │   └── ActionButtons.tsx   # Operator actions
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WebSocket hook
│   │   └── useAlerts.ts        # Alert state
│   ├── services/
│   │   └── api.ts              # REST client
│   └── types/
│       └── index.ts            # TypeScript types
```

### Scripts Directory

Create the following structure:

```
scripts/
├── setup_dataset.sh            # Download/prepare L5Kit data
├── run_demo.sh                 # Deterministic demo script
└── seed_golden_scenes.py       # Extract 3 scenes
```

### Tests Directory

Create the following structure:

```
tests/
├── unit/
│   ├── test_features.py
│   ├── test_anomalies.py
│   └── test_replay.py
└── integration/
    └── test_kafka_flow.py
```

### Docs Directory

Ensure the following exists:

```
docs/
├── architecture.md
├── kafka_schemas.md
└── demo_script.md
```

## Setting Up Files

### 1. Create All Directories

```bash
# Create service directories
mkdir -p services/replay-service/dataset
mkdir -p services/replay-service/replay
mkdir -p services/anomaly-service/features
mkdir -p services/anomaly-service/anomalies
mkdir -p services/operator-service/models
mkdir -p services/operator-service/db/migrations
mkdir -p services/operator-service/api
mkdir -p services/operator-service/websocket

# Create UI directories
mkdir -p ui/src/components
mkdir -p ui/src/hooks
mkdir -p ui/src/services
mkdir -p ui/src/types

# Create other directories
mkdir -p scripts
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p docs
```

### 2. Create Empty `__init__.py` Files

```bash
# Services
touch services/__init__.py
touch services/replay-service/__init__.py
touch services/replay-service/dataset/__init__.py
touch services/replay-service/replay/__init__.py
touch services/anomaly-service/__init__.py
touch services/anomaly-service/features/__init__.py
touch services/anomaly-service/anomalies/__init__.py
touch services/operator-service/__init__.py
touch services/operator-service/models/__init__.py
touch services/operator-service/db/__init__.py
touch services/operator-service/api/__init__.py
touch services/operator-service/websocket/__init__.py
```

### 3. Create Docker Compose Skeleton

Create `docker-compose.yml` with service definitions (no implementation yet):

```yaml
version: '3.8'

services:
  postgres:
    # Postgres configuration (from Phase 0)
    
  kafka:
    # Kafka configuration (from Phase 0)
    
  replay-service:
    # Placeholder for replay service
    
  anomaly-service:
    # Placeholder for anomaly service
    
  operator-service:
    # Placeholder for operator service
```

### 4. Update `.gitignore`

Ensure `.gitignore` includes:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnp
.pnp.js

# Docker
.dockerignore

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Dataset (if large)
dataset/
*.zarr
```

## What "Good" Output Looks Like

### Directory Structure Verification

```bash
# Verify structure
tree -L 3 services/
tree -L 3 ui/
tree -L 2 scripts/
tree -L 2 tests/
```

**Expected**: All directories exist with proper nesting.

### File Verification

```bash
# Check __init__.py files exist
find services -name "__init__.py" | wc -l
# Should return count of __init__.py files
```

**Expected**: All Python packages have `__init__.py` files.

### Docker Compose Validation

```bash
# Validate docker-compose.yml syntax
docker-compose config
```

**Expected**: No syntax errors, services are defined.

## Common Failure Modes and Fixes

### Directory Creation Issues

**Problem**: `mkdir -p` fails with permission errors
- **Fix**: Check directory permissions: `ls -la`
- **Fix**: Use `sudo` if necessary (not recommended for project directories)
- **Fix**: Ensure you're in the correct workspace directory

**Problem**: Directories created in wrong location
- **Fix**: Verify current directory: `pwd`
- **Fix**: Use absolute paths or navigate to project root first

### Missing `__init__.py` Files

**Problem**: Python imports fail with "No module named X"
- **Fix**: Ensure all package directories have `__init__.py`
- **Fix**: Verify file exists: `ls services/replay-service/__init__.py`

### Docker Compose Issues

**Problem**: `docker-compose config` fails
- **Fix**: Check YAML syntax (indentation, colons, etc.)
- **Fix**: Validate against docker-compose schema
- **Fix**: Ensure version is specified correctly

**Problem**: Services not recognized
- **Fix**: Verify service names match expected structure
- **Fix**: Check indentation in YAML file

### Git Ignore Issues

**Problem**: Unwanted files committed to git
- **Fix**: Verify `.gitignore` patterns match file types
- **Fix**: Use `git check-ignore -v <file>` to test patterns
- **Fix**: Remove already-tracked files: `git rm --cached <file>`

## Verification Checklist

After Phase 1 is complete:

- [ ] All service directories created
- [ ] All `__init__.py` files in place
- [ ] UI directory structure created
- [ ] Scripts directory created
- [ ] Tests directory structure created
- [ ] `docker-compose.yml` skeleton with service definitions
- [ ] `.gitignore` includes Python, Node, Docker artifacts
- [ ] Directory structure matches plan specification

## Next Steps

After Phase 1 is complete:
1. Repository structure is established
2. Service boundaries are defined
3. Foundation is ready for implementation

**Phase 2** will define Kafka topics, schemas, and message formats.

