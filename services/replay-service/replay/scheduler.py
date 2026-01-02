"""Frame timing scheduler.

Implements frame timing logic for replay rate control.
Fixed replay rate: 10 Hz (100ms per frame).
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Fixed replay rate: 10 Hz = 100ms per frame
REPLAY_RATE_HZ = 10.0
FRAME_INTERVAL_SECONDS = 1.0 / REPLAY_RATE_HZ


class ReplayScheduler:
    """Scheduler for fixed-rate replay timing.
    
    Maintains 10 Hz replay rate (100ms per frame).
    Uses wall-clock time to ensure consistent timing.
    """

    def __init__(self, replay_rate_hz: float = REPLAY_RATE_HZ):
        """Initialize scheduler.
        
        Args:
            replay_rate_hz: Target replay rate in Hz (default: 10.0)
        """
        self.replay_rate_hz = replay_rate_hz
        self.frame_interval = 1.0 / replay_rate_hz
        self.last_frame_time: Optional[float] = None
        self.frame_count = 0
        
        logger.info(f"Initialized scheduler with rate {replay_rate_hz} Hz (interval: {self.frame_interval:.3f}s)")

    def start(self) -> None:
        """Start the scheduler.
        
        Resets timing state for a new replay session.
        """
        self.last_frame_time = time.time()
        self.frame_count = 0
        logger.info("Scheduler started")

    def wait_for_next_frame(self) -> None:
        """Wait until it's time for the next frame.
        
        Uses wall-clock time to maintain fixed replay rate.
        Sleeps if necessary to maintain timing.
        """
        if self.last_frame_time is None:
            # First frame - start timing now
            self.last_frame_time = time.time()
            return
        
        # Calculate when next frame should occur
        next_frame_time = self.last_frame_time + self.frame_interval
        current_time = time.time()
        
        # Sleep if we're ahead of schedule
        sleep_duration = next_frame_time - current_time
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        
        # Update last frame time (use actual time to prevent drift)
        self.last_frame_time = time.time()
        self.frame_count += 1

    def get_elapsed_time(self) -> float:
        """Get elapsed time since scheduler started.
        
        Returns:
            Elapsed time in seconds
        """
        if self.last_frame_time is None:
            return 0.0
        
        return time.time() - (self.last_frame_time - (self.frame_count * self.frame_interval))

    def reset(self) -> None:
        """Reset the scheduler.
        
        Clears timing state.
        """
        self.last_frame_time = None
        self.frame_count = 0
        logger.info("Scheduler reset")
