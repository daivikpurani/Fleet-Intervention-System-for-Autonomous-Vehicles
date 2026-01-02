"""FastAPI application for replay service.

Minimal FastAPI surface with endpoints for:
- Starting/stopping replay
- Replay status
"""

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import ReplayConfig
from .dataset.normalizer import TelemetryNormalizer
from .dataset.reader import DatasetReader
from .kafka_producer import KafkaProducer
from .replay.engine import ReplayEngine
from .replay.scheduler import ReplayScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Replay Service", version="1.0.0")


# Request models
class StartReplayRequest(BaseModel):
    """Request model for starting replay."""
    scene_ids: Optional[List[int]] = None

# Global state
_config: Optional[ReplayConfig] = None
_reader: Optional[DatasetReader] = None
_producer: Optional[KafkaProducer] = None
_scheduler: Optional[ReplayScheduler] = None
_normalizer: Optional[TelemetryNormalizer] = None
_engine: Optional[ReplayEngine] = None


def _initialize_components():
    """Initialize all components."""
    global _config, _reader, _producer, _scheduler, _normalizer, _engine
    
    if _config is None:
        _config = ReplayConfig()
        logger.info(f"Loaded config: dataset={_config.dataset_path}, rate={_config.replay_rate_hz} Hz")
    
    if _reader is None:
        _reader = DatasetReader(_config.dataset_path)
        logger.info("Initialized dataset reader")
    
    if _producer is None:
        _producer = KafkaProducer(_config)
        logger.info("Initialized Kafka producer")
    
    if _scheduler is None:
        _scheduler = ReplayScheduler(_config.replay_rate_hz)
        logger.info("Initialized replay scheduler")
    
    if _normalizer is None:
        _normalizer = TelemetryNormalizer()
        logger.info("Initialized telemetry normalizer")
    
    if _engine is None:
        _engine = ReplayEngine(_reader, _producer, _scheduler, _normalizer)
        logger.info("Initialized replay engine")


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    _initialize_components()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _engine, _producer
    
    if _engine:
        _engine.stop()
    
    if _producer:
        _producer.close()
    
    logger.info("Shutdown complete")


@app.post("/replay/start")
async def start_replay(request: StartReplayRequest):
    """Start replay.
    
    Args:
        request: Request body with optional scene_ids list. If None or empty, replays all scenes.
    
    Returns:
        JSON response with status
    """
    _initialize_components()
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    
    if _engine.get_status()['active']:
        raise HTTPException(status_code=400, detail="Replay already running")
    
    try:
        scene_ids = request.scene_ids
        _engine.start(scene_ids)
        return JSONResponse(
            content={
                "status": "started",
                "message": f"Replay started for {len(scene_ids) if scene_ids else 'all'} scene(s)",
            }
        )
    except Exception as e:
        logger.error(f"Failed to start replay: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start replay: {str(e)}")


@app.post("/replay/stop")
async def stop_replay():
    """Stop replay.
    
    Returns:
        JSON response with status
    """
    _initialize_components()
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    
    if not _engine.get_status()['active']:
        raise HTTPException(status_code=400, detail="Replay not running")
    
    try:
        _engine.stop()
        return JSONResponse(
            content={
                "status": "stopped",
                "message": "Replay stopped",
            }
        )
    except Exception as e:
        logger.error(f"Failed to stop replay: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop replay: {str(e)}")


@app.get("/replay/status")
async def get_replay_status():
    """Get replay status.
    
    Returns:
        JSON response with status information:
        - active: Whether replay is running
        - scene_id: Current scene ID (or None)
        - frame_index: Current frame index (or None)
        - replay_rate: Current replay rate in Hz
    """
    _initialize_components()
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    
    status = _engine.get_status()
    return JSONResponse(content=status)


@app.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        JSON response with health status
    """
    return JSONResponse(content={"status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
