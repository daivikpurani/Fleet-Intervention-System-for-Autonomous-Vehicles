#!/bin/bash
# Phase 3 determinism restart test for FleetOps replay-service

set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

REPLAY_SERVICE_URL="http://localhost:8000"
SCENE_ID=1
NUM_EVENTS=30
OUTPUT_DIR="test_output"
RUN1_FILE="${OUTPUT_DIR}/run1.jsonl"
RUN2_FILE="${OUTPUT_DIR}/run2.jsonl"

echo "=========================================="
echo "Phase 3 Determinism Restart Test"
echo "=========================================="
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Check if replay service is running
echo "Checking replay service..."
if ! curl -s "${REPLAY_SERVICE_URL}/health" > /dev/null; then
    echo "ERROR: Replay service is not running at ${REPLAY_SERVICE_URL}"
    exit 1
fi
echo "✓ Replay service is running"
echo ""

# Stop any running replay
echo "Stopping any running replay..."
curl -s -X POST "${REPLAY_SERVICE_URL}/replay/stop" > /dev/null || true
sleep 1
echo ""

# Wait a moment for topic to settle
echo "Waiting for Kafka topic to settle..."
sleep 2
echo ""

# RUN 1: Start consumer, then start replay
echo "=========================================="
echo "RUN 1: Starting replay and capturing events"
echo "=========================================="

# Start consumer in background (without --from-beginning, will start from latest)
echo "Starting Kafka consumer (will capture from new messages)..."
python3 scripts/capture_kafka_events.py "${RUN1_FILE}" "${NUM_EVENTS}" &
CONSUMER_PID=$!

# Give consumer a moment to start
sleep 1

# Start replay
echo "Starting replay with scene_id=${SCENE_ID}..."
REPLAY_RESPONSE=$(curl -X POST "${REPLAY_SERVICE_URL}/replay/start" \
    -H "Content-Type: application/json" \
    -d "{\"scene_ids\": [${SCENE_ID}]}" \
    -s)
if command -v jq &> /dev/null; then
    echo "$REPLAY_RESPONSE" | jq .
else
    echo "$REPLAY_RESPONSE"
fi

# Wait for consumer to finish
echo "Waiting for consumer to capture ${NUM_EVENTS} events..."
wait $CONSUMER_PID
CONSUMER_EXIT=$?

if [ $CONSUMER_EXIT -ne 0 ]; then
    echo "ERROR: Consumer failed to capture events"
    exit 1
fi

if [ ! -f "${RUN1_FILE}" ] || [ ! -s "${RUN1_FILE}" ]; then
    echo "ERROR: ${RUN1_FILE} was not created or is empty"
    exit 1
fi

EVENT_COUNT=$(wc -l < "${RUN1_FILE}")
echo "✓ Captured ${EVENT_COUNT} events to ${RUN1_FILE}"
echo ""

# Stop replay
echo "Stopping replay..."
STOP_RESPONSE=$(curl -s -X POST "${REPLAY_SERVICE_URL}/replay/stop")
if command -v jq &> /dev/null; then
    echo "$STOP_RESPONSE" | jq .
else
    echo "$STOP_RESPONSE"
fi
sleep 2
echo ""

# RUN 2: Start consumer, then start replay again
echo "=========================================="
echo "RUN 2: Restarting replay and capturing events"
echo "=========================================="

# Start consumer in background (without --from-beginning, will start from latest)
echo "Starting Kafka consumer (will capture from new messages)..."
python3 scripts/capture_kafka_events.py "${RUN2_FILE}" "${NUM_EVENTS}" &
CONSUMER_PID=$!

# Give consumer a moment to start
sleep 1

# Start replay again
echo "Starting replay again with scene_id=${SCENE_ID}..."
REPLAY_RESPONSE=$(curl -X POST "${REPLAY_SERVICE_URL}/replay/start" \
    -H "Content-Type: application/json" \
    -d "{\"scene_ids\": [${SCENE_ID}]}" \
    -s)
if command -v jq &> /dev/null; then
    echo "$REPLAY_RESPONSE" | jq .
else
    echo "$REPLAY_RESPONSE"
fi

# Wait for consumer to finish
echo "Waiting for consumer to capture ${NUM_EVENTS} events..."
wait $CONSUMER_PID
CONSUMER_EXIT=$?

if [ $CONSUMER_EXIT -ne 0 ]; then
    echo "ERROR: Consumer failed to capture events"
    exit 1
fi

if [ ! -f "${RUN2_FILE}" ] || [ ! -s "${RUN2_FILE}" ]; then
    echo "ERROR: ${RUN2_FILE} was not created or is empty"
    exit 1
fi

EVENT_COUNT=$(wc -l < "${RUN2_FILE}")
echo "✓ Captured ${EVENT_COUNT} events to ${RUN2_FILE}"
echo ""

# Stop replay
echo "Stopping replay..."
STOP_RESPONSE=$(curl -s -X POST "${REPLAY_SERVICE_URL}/replay/stop")
if command -v jq &> /dev/null; then
    echo "$STOP_RESPONSE" | jq .
else
    echo "$STOP_RESPONSE"
fi
echo ""

# Compare results
echo "=========================================="
echo "Comparing results"
echo "=========================================="
python3 scripts/compare_determinism.py "${RUN1_FILE}" "${RUN2_FILE}"
COMPARE_EXIT=$?

echo ""
echo "=========================================="
if [ $COMPARE_EXIT -eq 0 ]; then
    echo "✓ Determinism test PASSED"
    echo "=========================================="
    exit 0
else
    echo "✗ Determinism test FAILED"
    echo "=========================================="
    exit 1
fi

