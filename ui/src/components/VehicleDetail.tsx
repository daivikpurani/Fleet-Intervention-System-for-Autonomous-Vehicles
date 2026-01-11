import { useState } from "react";
import type { Vehicle } from "../types";
import { Switch } from "./ui/switch";
import { Badge } from "./ui/badge";
import { ChevronRight } from "lucide-react";
import { cn } from "../lib/utils";

interface VehicleDetailProps {
  vehicle: Vehicle | null;
}

export function VehicleDetail({ vehicle }: VehicleDetailProps) {
  const [heatEnabled, setHeatEnabled] = useState(true);

  if (!vehicle) {
    return (
      <div className="p-8 text-center text-gray-500 text-sm">
        Select a vehicle to view details
      </div>
    );
  }

  // Format speed for display (m/s to km/h)
  const speedKmh = vehicle.last_speed != null 
    ? (vehicle.last_speed * 3.6).toFixed(1) 
    : null;
  
  // Format heading (radians to degrees)
  const headingDeg = vehicle.last_yaw != null 
    ? ((vehicle.last_yaw * 180 / Math.PI + 360) % 360).toFixed(0)
    : null;

  const vehicleDisplayId = vehicle.vehicle_display_id || vehicle.vehicle_id;
  const isEgo = vehicle.vehicle_type === "Autonomous Vehicle" || vehicle.vehicle_id.includes("ego");

  return (
    <div className="p-4 border-b border-gray-200">
      {/* Top Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-700">Heat</span>
          <Switch
            checked={heatEnabled}
            onCheckedChange={setHeatEnabled}
          />
        </div>
        <select className="text-xs font-semibold text-gray-700 bg-white border border-gray-300 rounded px-2 py-1">
          <option>Vlee 071</option>
        </select>
      </div>

      {/* Vehicle ID with LIVE tag */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono font-bold text-lg text-gray-900">
            {vehicleDisplayId}
          </span>
          <Badge className="bg-green-100 text-green-700 border-green-300 text-[10px] font-bold px-1.5 py-0.5">
            LIVE
          </Badge>
        </div>
        <div className="text-xs text-gray-600">
          Tracked Vehicle
        </div>
      </div>

      {/* Vehicle Type and ID */}
      <div className="mb-4 space-y-1">
        <div className="text-xs text-gray-600">
          PEREST SIAL WERVEES-4
        </div>
        <div className="text-xs font-mono text-gray-700">
          821
        </div>
      </div>

      {/* Speed */}
      {speedKmh && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-0.5">Speed</div>
          <div className="text-sm font-semibold text-gray-900 font-mono">
            {speedKmh} km/h
          </div>
        </div>
      )}

      {/* Heading */}
      {headingDeg && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-0.5">Heading</div>
          <div className="text-sm font-semibold text-gray-900 font-mono">
            {headingDeg}°
          </div>
        </div>
      )}

      {/* Position */}
      {vehicle.last_position_x !== null && vehicle.last_position_y !== null && (
        <div className="flex items-center gap-2">
          <div className="text-xs text-gray-600 font-mono">
            {vehicle.last_position_x.toFixed(4)} a
          </div>
          <div className="text-xs text-gray-600 font-mono">
            Y -{Math.abs(vehicle.last_position_y).toFixed(0)}, 45 s
          </div>
          <ChevronRight className="w-3 h-3 text-gray-400" />
        </div>
      )}
    </div>
  );
}
