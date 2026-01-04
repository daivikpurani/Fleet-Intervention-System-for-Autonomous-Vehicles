# Autonomous Fleet Response System - Demo Guide

## Quick Start

Run the complete demo with a single command:

```bash
make demo
```

Or directly:

```bash
./scripts/run_demo.sh
```

This script will:
1. ✅ Start infrastructure (Postgres, Kafka)
2. ✅ Start all backend services (replay, anomaly, operator)
3. ✅ Clear old data from database
4. ✅ Start the demo replay at 1 Hz
5. ✅ Launch the frontend UI

## Options

### Skip Frontend
If you only want to run the backend:

```bash
./scripts/run_demo.sh --no-frontend
```

### Skip Infrastructure
If infrastructure is already running:

```bash
./scripts/run_demo.sh --skip-infra
```

## What You'll See

- **Dashboard**: Open http://localhost:5173 in your browser
- **Real-time Alerts**: Alerts stream in with human-readable IDs (INC-XXXX)
- **Vehicle Tracking**: Vehicles show as VH-XXXX or AV-SF01 (ego vehicle)
- **Fleet Status**: Live statistics showing total vehicles, alerts, and status

## Demo Features

- **Human-Readable IDs**: 
  - Vehicles: `VH-4B2F`, `AV-SF01` (ego)
  - Incidents: `INC-7K3P2`
  - Scenes: `RUN-0104-A`

- **Demo Pacing**: 1 Hz replay rate (1 frame/second) for better visibility

- **Real-time Streaming**: Alerts appear instantly via WebSocket

- **Professional UI**: Mission control aesthetic with fleet status bar

## Stopping the Demo

Press `Ctrl+C` to stop all services. Infrastructure (Postgres, Kafka) will continue running.

To stop infrastructure:

```bash
make down
```

## Troubleshooting

### Services won't start
- Check Docker is running: `docker info`
- Check ports aren't in use: `lsof -i :8000`, `lsof -i :8003`
- View logs: `tail -f /tmp/replay-service.log`

### No alerts appearing
- Check Kafka is healthy: `make health`
- Check services are running: `ps aux | grep -E "(replay|anomaly|operator)"`
- Verify replay is active: `curl http://localhost:8000/replay/status`

### Database issues
- Reset database: `docker-compose exec postgres psql -U postgres -d fleetops -c "DELETE FROM alerts; DELETE FROM vehicle_state;"`
- Check migrations: `cd services/operator-service && alembic upgrade head`

## Manual Steps (if needed)

If you prefer to start services manually:

1. **Start infrastructure:**
   ```bash
   make up
   ```

2. **Start backend services:**
   ```bash
   ./scripts/start_all.sh
   ```

3. **Start demo replay:**
   ```bash
   curl -X POST http://localhost:8000/demo/start
   ```

4. **Open frontend:**
   ```bash
   cd ui && npm run dev
   ```

## Demo Duration

- **Quick Demo**: ~2 minutes (single scene, key anomalies)
- **Full Demo**: ~5-10 minutes (multiple scenes, complete workflow)

The demo automatically stops when the replay completes.

