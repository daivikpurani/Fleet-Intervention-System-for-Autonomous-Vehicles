# Check 4: Verify Anomalies are Emitted to Kafka

## Quick Start

Run the check script:
```bash
source venv/bin/activate
python3 scripts/check4_anomalies.py
```

## Prerequisites

Before running Check 4, you need:

1. **Kafka running**
   ```bash
   make up
   # Wait for Kafka to be healthy
   ```

2. **Replay-service running**
   ```bash
   source venv/bin/activate
   PYTHONPATH=. uvicorn services.replay-service.main:app --host 0.0.0.0 --port 8001
   ```

3. **Anomaly-service running** (in a separate terminal)
   ```bash
   source venv/bin/activate
   cd services/anomaly-service
   PYTHONPATH=../.. python3 -m services.anomaly_service.main
   ```
   
   Or if that doesn't work due to import issues, you can run it directly:
   ```bash
   source venv/bin/activate
   cd services/anomaly-service
   PYTHONPATH=../.. python3 -c "
   import sys
   sys.path.insert(0, '../..')
   from services.anomaly_service.main import main
   main()
   "
   ```

4. **Start replay**
   ```bash
   curl -X POST http://localhost:8001/replay/start \
     -H "Content-Type: application/json" \
     -d '{"scene_ids": [0]}'
   ```

5. **Run Check 4**
   ```bash
   python3 scripts/check4_anomalies.py
   ```

## Expected Output

If everything is working, you should see:
```
✓ CHECK 4 PASSED: Found X anomaly(ies)
```

The script will show details of each anomaly detected, including:
- Rule name (e.g., `sudden_deceleration`, `perception_instability`)
- Vehicle ID
- Scene ID and frame index
- Severity level (INFO, WARNING, or CRITICAL)
- Features and thresholds used

## Troubleshooting

If no anomalies are found:
1. Check that replay-service is actually replaying (check its logs)
2. Check that anomaly-service is consuming events (check its logs for "Consumed event" messages)
3. Try a different scene that might have more anomalies
4. Check that thresholds.json exists and is loaded correctly

