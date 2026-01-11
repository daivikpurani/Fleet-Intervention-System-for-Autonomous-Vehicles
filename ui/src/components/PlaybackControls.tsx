import { useState } from "react";
import { Play, Pause, SkipBack, SkipForward, Grid } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "../lib/utils";

export function PlaybackControls() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [frame, setFrame] = useState(237.463);

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleSpeedChange = () => {
    const speeds = [1, 2, 4, 8];
    const currentIndex = speeds.indexOf(speed);
    const nextIndex = (currentIndex + 1) % speeds.length;
    setSpeed(speeds[nextIndex]);
  };

  return (
    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-white border border-gray-300 rounded-lg shadow-lg px-4 py-2 flex items-center gap-3 z-10">
      {/* Skip Backward */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-gray-700 hover:bg-gray-100"
      >
        <SkipBack className="w-4 h-4" />
      </Button>

      {/* Play/Pause */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-gray-700 hover:bg-gray-100"
        onClick={handlePlayPause}
      >
        {isPlaying ? (
          <Pause className="w-4 h-4" />
        ) : (
          <Play className="w-4 h-4" />
        )}
      </Button>

      {/* Skip Forward */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-gray-700 hover:bg-gray-100"
      >
        <SkipForward className="w-4 h-4" />
      </Button>

      {/* Speed Multiplier */}
      <button
        onClick={handleSpeedChange}
        className="px-2 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100 rounded"
      >
        {speed}x
      </button>

      {/* Frame Counter */}
      <div className="px-2 py-1 text-xs font-mono text-gray-700 bg-gray-50 rounded">
        {frame.toFixed(3)}
      </div>

      {/* Grid Icon */}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-gray-700 hover:bg-gray-100"
      >
        <Grid className="w-4 h-4" />
      </Button>
    </div>
  );
}
