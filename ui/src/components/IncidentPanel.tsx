import { useTheme } from "../contexts/ThemeContext";
import type { Alert, Severity } from "../types";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { cn } from "../lib/utils";

interface IncidentPanelProps {
  alert: Alert | null;
}

export function IncidentPanel({ alert }: IncidentPanelProps) {
  if (!alert) {
    return (
      <div className="p-8 text-center text-gray-500 text-sm">
        Select an alert to view incident details
      </div>
    );
  }

  const incidentId = alert.incident_id || `INC-${alert.id.slice(0, 5).toUpperCase()}`;
  const vehicleDisplayId = alert.vehicle_display_id || alert.vehicle_id;
  const ruleName = alert.rule_display_name || alert.rule_name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  // Format feature values for display
  const formatValue = (key: string, value: any): string => {
    if (typeof value === "number") {
      if (key.includes("acceleration") || key.includes("speed") || key.includes("velocity") || key.includes("change")) {
        return `${value.toFixed(1)} m/s${key.includes("acceleration") ? "²" : ""}`;
      }
      if (key.includes("displacement") || key.includes("distance") || key.includes("jump")) {
        return `${value.toFixed(2)} m`;
      }
      return value.toFixed(3);
    }
    return String(value);
  };

  const features = alert.anomaly_payload?.features || {};
  const firstEvidence = Object.entries(features)[0];
  const evidenceText = firstEvidence 
    ? `${firstEvidence[0].replace(/_/g, " ")}: ${formatValue(firstEvidence[0], firstEvidence[1])}`
    : "No evidence available";

  // Format dates
  const formatEventTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  };

  return (
    <div className="p-4">
      {/* Header */}
      <h2 className="text-sm font-bold text-gray-700 mb-4 tracking-wide uppercase">
        Incident Details
      </h2>

      {/* Incident ID */}
      <div className="mb-4">
        <div className="font-mono font-bold text-lg text-gray-900 mb-2">
          {incidentId}
        </div>
        <div className="flex items-center gap-2">
          <Badge className={cn(
            "text-xs font-bold px-2 py-0.5 border",
            alert.severity === "CRITICAL" 
              ? "bg-red-100 text-red-700 border-red-300"
              : alert.severity === "WARNING"
              ? "bg-orange-100 text-orange-700 border-orange-300"
              : "bg-blue-100 text-blue-700 border-blue-300"
          )}>
            {alert.severity}
          </Badge>
          <Badge className={cn(
            "text-xs font-semibold px-2 py-0.5 border",
            alert.status === "OPEN"
              ? "bg-red-100 text-red-700 border-red-300"
              : alert.status === "ACKNOWLEDGED"
              ? "bg-orange-100 text-orange-700 border-orange-300"
              : "bg-green-100 text-green-700 border-green-300"
          )}>
            {alert.status}
          </Badge>
        </div>
      </div>

      {/* Detection Rule */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 mb-1 uppercase tracking-wide font-semibold">
          Detection Rule
        </div>
        <div className="text-sm font-semibold text-gray-900">
          {ruleName}
        </div>
      </div>

      {/* Context */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 mb-1 uppercase tracking-wide font-semibold">
          Context
        </div>
        <div className="text-sm font-mono font-semibold text-gray-900">
          {vehicleDisplayId}
        </div>
      </div>

      {/* Timeline */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide font-semibold">
          Timeline
        </div>
        <div className="space-y-1 text-xs text-gray-600">
          <div>
            <span className="text-gray-500">First event: </span>
            {formatEventTime(alert.first_seen_event_time)}
          </div>
          <div>
            <span className="text-gray-500">Last event: </span>
            {formatEventTime(alert.last_seen_event_time)}
          </div>
          <div>
            <span className="text-gray-500">Frame: </span>
            <span className="font-mono">{alert.frame_index}</span>
          </div>
        </div>
      </div>

      {/* Evidence */}
      <div className="mb-4">
        <div className="text-xs text-gray-500 mb-1 uppercase tracking-wide font-semibold">
          Evidence
        </div>
        <div className="text-xs text-gray-700 font-mono">
          {evidenceText}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1 h-9 text-xs font-semibold bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
        >
          Acknowledge
        </Button>
        <Button
          size="sm"
          className="flex-1 h-9 text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700"
        >
          Respond
        </Button>
      </div>
    </div>
  );
}
