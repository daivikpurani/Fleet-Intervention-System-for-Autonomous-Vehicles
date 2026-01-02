"""FastAPI application with WebSocket support for operator service."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .config import OperatorConfig
from .db.models import Base, Alert, AlertStatus
from .db import session as db_session
from .kafka_consumer import KafkaConsumer, TelemetryConsumer
from .services.alert_service import AlertService
from .services.vehicle_state_service import VehicleStateService
from .websocket.handler import websocket_manager
from .api import alerts, vehicles, actions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global config
config = OperatorConfig()

# Background task handles
_kafka_task: asyncio.Task | None = None
_telemetry_task: asyncio.Task | None = None
_executor: ThreadPoolExecutor | None = None


# Global event loop reference for scheduling async operations from threads
_event_loop: asyncio.AbstractEventLoop | None = None


def _process_kafka_event(event) -> None:
    """Process a single Kafka event (runs in thread)."""
    # Create a new database session for each message
    if db_session.SessionLocal is None:
        logger.error("Database not initialized. Cannot process events.")
        return
    
    db = db_session.SessionLocal()
    try:
        alert = AlertService.process_anomaly_event(event, db)

        # Broadcast alert event (schedule coroutine in event loop)
        from .models.alerts import AlertResponse
        alert_response = AlertResponse.model_validate(alert)

        # Determine if this is a new alert or update
        event_type = "alert_created" if alert.first_seen_event_time == alert.last_seen_event_time else "alert_updated"

        # Schedule WebSocket broadcast in event loop from thread
        global _event_loop
        if _event_loop and _event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast(event_type, alert_response.model_dump()),
                _event_loop
            )

        # Also broadcast vehicle update
        vehicle_state = VehicleStateService.update_state(event.vehicle_id, db)
        from .models.vehicles import VehicleResponse
        open_alerts_count = db.query(Alert).filter(
            Alert.vehicle_id == event.vehicle_id,
            Alert.status == AlertStatus.OPEN
        ).count()
        vehicle_response = VehicleResponse(
            vehicle_id=vehicle_state.vehicle_id,
            state=vehicle_state.state,
            assigned_operator=vehicle_state.assigned_operator,
            last_position_x=vehicle_state.last_position_x,
            last_position_y=vehicle_state.last_position_y,
            updated_at=vehicle_state.updated_at,
            open_alerts_count=open_alerts_count,
        )
        
        if _event_loop and _event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                websocket_manager.broadcast("vehicle_updated", vehicle_response.model_dump()),
                _event_loop
            )

    except Exception as e:
        logger.error(f"Error processing anomaly event: {e}", exc_info=True)
    finally:
        db.close()


def _process_telemetry_event(event) -> None:
    """Process a single telemetry event (runs in thread)."""
    # Create a new database session for each message
    if db_session.SessionLocal is None:
        logger.error("Database not initialized. Cannot process telemetry events.")
        return
    
    db = db_session.SessionLocal()
    try:
        # Update vehicle position
        centroid = event.centroid
        position_x = centroid.get('x')
        position_y = centroid.get('y')
        
        if position_x is not None and position_y is not None:
            vehicle_state = VehicleStateService.update_position(
                event.vehicle_id,
                float(position_x),
                float(position_y),
                db
            )
            
            # Broadcast vehicle update with position
            from .models.vehicles import VehicleResponse
            open_alerts_count = db.query(Alert).filter(
                Alert.vehicle_id == event.vehicle_id,
                Alert.status == AlertStatus.OPEN
            ).count()
            vehicle_response = VehicleResponse(
                vehicle_id=vehicle_state.vehicle_id,
                state=vehicle_state.state,
                assigned_operator=vehicle_state.assigned_operator,
                last_position_x=vehicle_state.last_position_x,
                last_position_y=vehicle_state.last_position_y,
                updated_at=vehicle_state.updated_at,
                open_alerts_count=open_alerts_count,
            )
            
            global _event_loop
            if _event_loop and _event_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    websocket_manager.broadcast("vehicle_updated", vehicle_response.model_dump()),
                    _event_loop
                )
    except Exception as e:
        logger.error(f"Error processing telemetry event: {e}", exc_info=True)
    finally:
        db.close()


def _run_kafka_consumer() -> None:
    """Run Kafka consumer in thread (blocking)."""
    logger.info("Starting Kafka consumer in background thread")
    consumer = KafkaConsumer(config)

    try:
        for event in consumer.consume():
            # Process event
            _process_kafka_event(event)
    except Exception as e:
        logger.error(f"Fatal error in Kafka consumer: {e}", exc_info=True)
    finally:
        consumer.close()


def _run_telemetry_consumer() -> None:
    """Run telemetry consumer in thread (blocking)."""
    logger.info("Starting telemetry consumer in background thread")
    consumer = TelemetryConsumer(config)

    try:
        for event in consumer.consume():
            # Process event
            _process_telemetry_event(event)
    except Exception as e:
        logger.error(f"Fatal error in telemetry consumer: {e}", exc_info=True)
    finally:
        consumer.close()


async def kafka_consumer_task() -> None:
    """Background task wrapper for Kafka consumer (runs consumer in thread)."""
    global _executor, _event_loop
    if _event_loop is None:
        _event_loop = asyncio.get_event_loop()
    
    # Executor should be initialized before tasks are created
    if _executor is None:
        logger.error("ThreadPoolExecutor not initialized. Cannot run Kafka consumer.")
        return
    
    try:
        # Run blocking Kafka consumer in thread pool
        await asyncio.get_event_loop().run_in_executor(_executor, _run_kafka_consumer)
    except Exception as e:
        logger.error(f"Kafka consumer task error: {e}", exc_info=True)


async def telemetry_consumer_task() -> None:
    """Background task wrapper for telemetry consumer (runs consumer in thread)."""
    global _executor, _event_loop
    if _event_loop is None:
        _event_loop = asyncio.get_event_loop()
    
    # Executor should be initialized before tasks are created
    if _executor is None:
        logger.error("ThreadPoolExecutor not initialized. Cannot run telemetry consumer.")
        return
    
    try:
        # Run blocking telemetry consumer in thread pool
        await asyncio.get_event_loop().run_in_executor(_executor, _run_telemetry_consumer)
    except Exception as e:
        logger.error(f"Telemetry consumer task error: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting operator service")
    db_session.init_db(config)

    # Set config in API modules
    alerts.set_config(config)
    vehicles.set_config(config)

    # Initialize shared thread pool executor for consumer tasks
    # Create with 2 workers: one for Kafka consumer, one for telemetry consumer
    global _executor, _event_loop
    _event_loop = asyncio.get_event_loop()
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kafka-consumer")

    # Start Kafka consumer background tasks
    global _kafka_task, _telemetry_task
    _kafka_task = asyncio.create_task(kafka_consumer_task())
    _telemetry_task = asyncio.create_task(telemetry_consumer_task())

    yield

    # Shutdown
    logger.info("Shutting down operator service")
    global _kafka_task, _telemetry_task
    if _kafka_task:
        _kafka_task.cancel()
        try:
            await _kafka_task
        except asyncio.CancelledError:
            pass
    if _telemetry_task:
        _telemetry_task.cancel()
        try:
            await _telemetry_task
        except asyncio.CancelledError:
            pass
    
    # Shutdown thread pool executor
    global _executor
    if _executor:
        _executor.shutdown(wait=True)
        _executor = None


app = FastAPI(
    title="Operator Service",
    description="Alert lifecycle management and operator actions",
    lifespan=lifespan,
)

# Include routers
app.include_router(alerts.router)
app.include_router(vehicles.router)
app.include_router(actions.router)


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive by receiving messages
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        websocket_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
