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
    demo_mode: bool = False  # If True, uses slower 1 Hz rate for demos

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
        request: Request body with optional scene_ids list and demo_mode flag.
            - scene_ids: If None or empty, replays all scenes.
            - demo_mode: If True, uses slower 1 Hz rate suitable for demos.
    
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
        
        # Set demo mode on scheduler if requested
        if _scheduler is not None:
            _scheduler.set_demo_mode(request.demo_mode)
        
        _engine.start(scene_ids)
        
        mode_str = "demo mode (1 Hz)" if request.demo_mode else "normal mode (10 Hz)"
        return JSONResponse(
            content={
                "status": "started",
                "message": f"Replay started for {len(scene_ids) if scene_ids else 'all'} scene(s) in {mode_str}",
                "demo_mode": request.demo_mode,
                "replay_rate_hz": 1.0 if request.demo_mode else 10.0,
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
        - demo_mode: Whether demo mode is enabled
    """
    _initialize_components()
    
    if _engine is None:
        raise HTTPException(status_code=500, detail="Replay engine not initialized")
    
    status = _engine.get_status()
    
    # Add demo_mode to status
    if _scheduler is not None:
        status['demo_mode'] = _scheduler.demo_mode
    
    return JSONResponse(content=status)


@app.get("/demo/scenes")
async def get_demo_scenes():
    """Get demo scenes configuration.
    
    Returns:
        JSON response with demo scenes info including:
        - List of curated scenes for demos
        - Recommended settings
        - Scene descriptions and expected alerts
    """
    _initialize_components()
    
    if _config is None:
        raise HTTPException(status_code=500, detail="Config not initialized")
    
    demo_config = _config.load_demo_scenes()
    if demo_config is None:
        return JSONResponse(
            content={
                "scenes": [{"id": 0, "name": "Default Scene"}],
                "demo_config": {"recommended_replay_rate_hz": 1.0}
            }
        )
    
    return JSONResponse(content=demo_config)


@app.post("/demo/start")
async def start_demo():
    """Start demo mode with curated scenes.
    
    This is a convenience endpoint that:
    1. Loads the demo scenes configuration
    2. Starts replay in demo mode (1 Hz) with those scenes
    
    Returns:
        JSON response with status
    """
    _initialize_components()
    
    if _engine is None or _config is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    if _engine.get_status()['active']:
        raise HTTPException(status_code=400, detail="Replay already running")
    
    try:
        # Get demo scene IDs
        scene_ids = _config.get_demo_scene_ids()
        
        # Enable demo mode on scheduler
        if _scheduler is not None:
            _scheduler.set_demo_mode(True)
        
        # Start replay
        _engine.start(scene_ids)
        
        return JSONResponse(
            content={
                "status": "started",
                "message": f"Demo started with {len(scene_ids)} scene(s) at 1 Hz",
                "scene_ids": scene_ids,
                "demo_mode": True,
                "replay_rate_hz": 1.0,
            }
        )
    except Exception as e:
        logger.error(f"Failed to start demo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start demo: {str(e)}")


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
