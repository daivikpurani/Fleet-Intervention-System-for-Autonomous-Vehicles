#!/usr/bin/env python3
"""Capture Kafka events from raw_telemetry topic.

Captures exactly N events and writes them to a JSONL file.
"""

import json
import sys
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError

def capture_events(output_file: str, num_events: int = 30, from_beginning: bool = False):
    """Capture events from raw_telemetry topic.
    
    Args:
        output_file: Path to output JSONL file
        num_events: Number of events to capture
        from_beginning: If True, start from beginning of topic
    """
    consumer = None
    try:
        # Create consumer
        consumer = KafkaConsumer(
            'raw_telemetry',
            bootstrap_servers='localhost:9092',
            auto_offset_reset='earliest' if from_beginning else 'latest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=60000,  # 60 second timeout (replay at 10Hz = 3s for 30 events, but allow buffer)
        )
        
        # Wait a moment for consumer to be ready
        time.sleep(0.5)
        
        print(f"Consumer ready. Waiting for events...")
        print(f"from_beginning={from_beginning}, num_events={num_events}")
        
        events_captured = 0
        with open(output_file, 'w') as f:
            for message in consumer:
                event = message.value
                # Write event as JSON line
                f.write(json.dumps(event, default=str) + '\n')
                f.flush()  # Ensure immediate write
                events_captured += 1
                print(f"Captured event {events_captured}/{num_events}: vehicle_id={event.get('vehicle_id')}, frame_index={event.get('frame_index')}")
                
                if events_captured >= num_events:
                    break
        
        print(f"\nCaptured {events_captured} events to {output_file}")
        return events_captured
        
    except KafkaError as e:
        print(f"Kafka error: {e}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 0
    finally:
        if consumer:
            consumer.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 capture_kafka_events.py <output_file> [num_events] [--from-beginning]")
        sys.exit(1)
    
    output_file = sys.argv[1]
    num_events = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    from_beginning = '--from-beginning' in sys.argv
    
    captured = capture_events(output_file, num_events, from_beginning)
    sys.exit(0 if captured == num_events else 1)

