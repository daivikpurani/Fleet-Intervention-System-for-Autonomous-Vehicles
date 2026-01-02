#!/usr/bin/env python3
"""Check 4: Verify anomalies are emitted to Kafka topic."""

import json
import sys
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError

print("=" * 60)
print("CHECK 4: Anomalies topic produces events")
print("=" * 60)

# Check Kafka availability
print("\n1. Checking Kafka availability...")
try:
    test_consumer = KafkaConsumer(
        bootstrap_servers="localhost:9092",
        consumer_timeout_ms=1000,
    )
    test_consumer.close()
    print("   ✓ Kafka is available at localhost:9092")
except Exception as e:
    print(f"   ✗ Kafka not available: {e}")
    print("\n   Please start Kafka with: make up")
    sys.exit(1)

# Consume from anomalies topic
print("\n2. Consuming from anomalies topic...")
print("   (Will wait up to 60 seconds for anomalies)")
print("   (Make sure replay-service and anomaly-service are running)")

consumer = None
try:
    consumer = KafkaConsumer(
        "anomalies",
        bootstrap_servers="localhost:9092",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        consumer_timeout_ms=60000,  # 60 second timeout
    )
    
    print("\n   Waiting for anomalies...")
    anomalies = []
    start_time = time.time()
    
    for message in consumer:
        anomaly = message.value
        anomalies.append(anomaly)
        elapsed = time.time() - start_time
        
        print(f"\n   ✓ Anomaly {len(anomalies)} received (after {elapsed:.1f}s):")
        print(f"     Rule: {anomaly.get('rule_name')}")
        print(f"     Vehicle: {anomaly.get('vehicle_id')}")
        print(f"     Scene: {anomaly.get('scene_id')}, Frame: {anomaly.get('frame_index')}")
        print(f"     Severity: {anomaly.get('severity')}")
        
        if len(anomalies) >= 5:  # Collect a few for verification
            break
    
    consumer.close()
    
    if len(anomalies) > 0:
        print(f"\n3. Verifying anomaly structure...")
        
        # Verify structure
        sample = anomalies[0]
        required_fields = [
            "anomaly_id",
            "vehicle_id",
            "scene_id",
            "frame_index",
            "rule_name",
            "features",
            "thresholds",
            "severity",
        ]
        
        missing_fields = [f for f in required_fields if f not in sample]
        if missing_fields:
            print(f"   ✗ Missing fields: {missing_fields}")
            sys.exit(1)
        
        print("   ✓ All required fields present")
        print(f"\n   Sample anomaly structure:")
        print(f"     - rule_name: {sample.get('rule_name')}")
        print(f"     - severity: {sample.get('severity')}")
        print(f"     - features: {list(sample.get('features', {}).keys())}")
        print(f"     - thresholds: {list(sample.get('thresholds', {}).keys())}")
        
        print(f"\n" + "=" * 60)
        print(f"✓ CHECK 4 PASSED: Found {len(anomalies)} anomaly(ies)")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("⚠ CHECK 4: No anomalies found")
        print("=" * 60)
        print("\nPossible reasons:")
        print("  1. Replay-service is not running or not replaying")
        print("  2. Anomaly-service is not running")
        print("  3. No anomalies detected in the replayed scene")
        print("\nTo fix:")
        print("  1. Start replay-service: uvicorn services.replay-service.main:app --port 8001")
        print("  2. Start replay: curl -X POST http://localhost:8001/replay/start -H 'Content-Type: application/json' -d '{\"scene_ids\": [0]}'")
        print("  3. Start anomaly-service (see README for instructions)")
        print("  4. Run this check again")
        sys.exit(1)
        
except KafkaError as e:
    print(f"\n✗ Kafka error: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    if consumer:
        consumer.close()
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    if consumer:
        try:
            consumer.close()
        except:
            pass

