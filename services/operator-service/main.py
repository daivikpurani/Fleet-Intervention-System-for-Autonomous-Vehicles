"""FastAPI application with WebSocket support for operator service."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .config import OperatorConfig
from .db.models import Base, Alert, AlertStatus
from .db.session import init_db, SessionLocal
from .kafka_consumer import KafkaConsumer
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

# Background task handle
_kafka_task: asyncio.Task | None = None


async def kafka_consumer_task() -> None:
    """Background task for consuming Kafka messages."""
    logger.info("Starting Kafka consumer background task")
    consumer = KafkaConsumer(config)

    try:
        for event in consumer.consume():
            # Create a new database session for each message
            db = SessionLocal()
            try:
                alert = AlertService.process_anomaly_event(event, db)

                # Broadcast alert event
                from .models.alerts import AlertResponse
                alert_response = AlertResponse.model_validate(alert)

                # Determine if this is a new alert or update
                event_type = "alert_created" if alert.first_seen_event_time == alert.last_seen_event_time else "alert_updated"

                await websocket_manager.broadcast(
                    event_type,
                    alert_response.model_dump()
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
                    updated_at=vehicle_state.updated_at,
                    open_alerts_count=open_alerts_count,
                )
                await websocket_manager.broadcast(
                    "vehicle_updated",
                    vehicle_response.model_dump()
                )

            except Exception as e:
                logger.error(f"Error processing anomaly event: {e}", exc_info=True)
                # Continue processing other events
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Fatal error in Kafka consumer task: {e}", exc_info=True)
    finally:
        consumer.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting operator service")
    init_db(config)

    # Set config in API modules
    alerts.set_config(config)
    vehicles.set_config(config)

    # Start Kafka consumer background task
    global _kafka_task
    _kafka_task = asyncio.create_task(kafka_consumer_task())

    yield

    # Shutdown
    logger.info("Shutting down operator service")
    if _kafka_task:
        _kafka_task.cancel()
        try:
            await _kafka_task
        except asyncio.CancelledError:
            pass


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
