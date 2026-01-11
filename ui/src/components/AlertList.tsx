import { useState, useMemo, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Search, Mail, ChevronDown, Download, MoreVertical } from "lucide-react";
import type { Alert, AlertStatus, Severity } from "../types";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { cn } from "../lib/utils";

interface AlertListProps {
  alerts: Alert[];
  onAlertClick: (alert: Alert) => void;
  demoMode?: boolean;
}

interface VehicleAlertGroup {
  vehicleId: string;
  vehicleDisplayId: string;
  vehicleType: string;
  highestSeverity: Severity;
  alertCount: number;
  openCount: number;
  uniqueRuleNames: string[];
  latestAlert: Alert;
  alerts: Alert[];
  lastUpdated: string;
}

const SEVERITY_PRIORITY: Record<Severity, number> = {
  CRITICAL: 3,
  WARNING: 2,
  INFO: 1,
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", { month: "2-digit", day: "2-digit", year: "numeric" });
}

function formatRuleName(ruleName: string): string {
  return ruleName
    .replace(/_/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace("Sudden Deceleration", "Hard Brake")
    .replace("Perception Instability", "Perception")
    .replace("Dropout Proxy", "Sensor Dropout");
}

export function AlertList({ alerts: allAlerts, onAlertClick, demoMode = false }: AlertListProps) {
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);
  const [expandedVehicleId, setExpandedVehicleId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Severity | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const onAlertClickRef = useRef(onAlertClick);
  useEffect(() => {
    onAlertClickRef.current = onAlertClick;
  }, [onAlertClick]);

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    let result = allAlerts;

    if (severityFilter !== "ALL") {
      result = result.filter((alert) => alert.severity === severityFilter);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((alert) =>
        alert.vehicle_id.toLowerCase().includes(query) ||
        (alert.vehicle_display_id && alert.vehicle_display_id.toLowerCase().includes(query))
      );
    }

    return result;
  }, [allAlerts, severityFilter, searchQuery]);

  // Group alerts by vehicle
  const vehicleGroups = useMemo(() => {
    const groupMap = new Map<string, VehicleAlertGroup>();

    for (const alert of filteredAlerts) {
      const vehicleId = alert.vehicle_id;
      
      if (!groupMap.has(vehicleId)) {
        const displayId = alert.vehicle_display_id || vehicleId;
        const isAV = displayId.startsWith("AV-") || vehicleId.includes("ego");
        
        groupMap.set(vehicleId, {
          vehicleId,
          vehicleDisplayId: displayId,
          vehicleType: isAV ? "Autonomous Vehicle" : "Tracked Vehicle",
          highestSeverity: alert.severity,
          alertCount: 0,
          openCount: 0,
          uniqueRuleNames: [],
          latestAlert: alert,
          alerts: [],
          lastUpdated: alert.last_seen_event_time,
        });
      }

      const group = groupMap.get(vehicleId)!;
      group.alerts.push(alert);
      group.alertCount++;
      
      if (alert.status === "OPEN") {
        group.openCount++;
      }

      if (SEVERITY_PRIORITY[alert.severity] > SEVERITY_PRIORITY[group.highestSeverity]) {
        group.highestSeverity = alert.severity;
      }

      const ruleName = alert.rule_display_name || alert.rule_name;
      if (!group.uniqueRuleNames.includes(ruleName)) {
        group.uniqueRuleNames.push(ruleName);
      }

      if (new Date(alert.last_seen_event_time) > new Date(group.lastUpdated)) {
        group.lastUpdated = alert.last_seen_event_time;
        group.latestAlert = alert;
      }
    }

    return Array.from(groupMap.values()).sort((a, b) => {
      const severityDiff = SEVERITY_PRIORITY[b.highestSeverity] - SEVERITY_PRIORITY[a.highestSeverity];
      if (severityDiff !== 0) return severityDiff;
      return new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime();
    });
  }, [filteredAlerts]);

  // Count alerts by severity
  const alertCounts = useMemo(() => {
    const openAlerts = allAlerts.filter((a) => a.status === "OPEN");
    return {
      all: vehicleGroups.length,
      critical: openAlerts.filter((a) => a.severity === "CRITICAL").length,
      warning: openAlerts.filter((a) => a.severity === "WARNING").length,
      info: openAlerts.filter((a) => a.severity === "INFO").length,
      total: openAlerts.length,
      vehicleCount: vehicleGroups.length,
    };
  }, [allAlerts, vehicleGroups]);

  // Demo mode: auto-select first vehicle
  useEffect(() => {
    if (demoMode && vehicleGroups.length > 0 && !selectedVehicleId) {
      const criticalGroup = vehicleGroups.find((g) => g.highestSeverity === "CRITICAL");
      const targetGroup = criticalGroup || vehicleGroups[0];
      setSelectedVehicleId(targetGroup.vehicleId);
      onAlertClickRef.current(targetGroup.latestAlert);
    }
  }, [demoMode, vehicleGroups, selectedVehicleId]);

  const handleGroupClick = (group: VehicleAlertGroup) => {
    setSelectedVehicleId(group.vehicleId);
    onAlertClick(group.latestAlert);
    
    if (selectedVehicleId === group.vehicleId) {
      setExpandedVehicleId(expandedVehicleId === group.vehicleId ? null : group.vehicleId);
    } else {
      setExpandedVehicleId(group.vehicleId);
    }
  };

  const getSeverityBadgeClass = (severity: Severity) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-red-500 text-white border-red-600";
      case "WARNING":
        return "bg-orange-500 text-white border-orange-600";
      case "INFO":
        return "bg-blue-500 text-white border-blue-600";
      default:
        return "bg-gray-500 text-white border-gray-600";
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        {/* Alert Summary */}
        <div className="mb-3">
          <div className="text-xs font-bold text-gray-900 mb-3">
            VEHICLES WITH ALERTS: {alertCounts.vehicleCount}
          </div>
        </div>

        {/* Filter Buttons */}
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setSeverityFilter("ALL")}
            className={cn(
              "h-7 px-3 text-xs font-semibold rounded-full transition-colors",
              severityFilter === "ALL" 
                ? "bg-yellow-500 text-white hover:bg-yellow-600" 
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
            )}
          >
            All {alertCounts.all}
          </button>
          <button
            onClick={() => setSeverityFilter("CRITICAL")}
            className={cn(
              "h-7 px-3 text-xs font-semibold rounded-full transition-colors",
              severityFilter === "CRITICAL"
                ? "bg-red-500 text-white hover:bg-red-600"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
            )}
          >
            Critical {alertCounts.critical}
          </button>
          <button
            onClick={() => setSeverityFilter("WARNING")}
            className={cn(
              "h-7 px-3 text-xs font-semibold rounded-full transition-colors",
              severityFilter === "WARNING"
                ? "bg-orange-500 text-white hover:bg-orange-600"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
            )}
          >
            Warning {alertCounts.warning}
          </button>
          <button
            onClick={() => setSeverityFilter("INFO")}
            className={cn(
              "h-7 px-3 text-xs font-semibold rounded-full transition-colors",
              severityFilter === "INFO"
                ? "bg-blue-500 text-white hover:bg-blue-600"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
            )}
          >
            Info {alertCounts.info}
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type="text"
            placeholder="Search vehicle..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-8 text-xs bg-gray-50 border-gray-300"
          />
        </div>
      </div>

      {/* Vehicle List */}
      <div className="flex-1 overflow-y-auto">
        {vehicleGroups.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            No vehicles with alerts
          </div>
        ) : (
          <div className="p-2">
            {vehicleGroups.map((group) => {
              const isSelected = selectedVehicleId === group.vehicleId;
              const isExpanded = expandedVehicleId === group.vehicleId;
              const severityClass = getSeverityBadgeClass(group.highestSeverity);
              const ruleDescription = group.uniqueRuleNames
                .slice(0, 2)
                .map(formatRuleName)
                .join(" / ");

              return (
                <motion.div
                  key={group.vehicleId}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-2"
                >
                  <div
                    onClick={() => handleGroupClick(group)}
                    className={cn(
                      "p-3 rounded border cursor-pointer transition-colors",
                      isSelected
                        ? "bg-blue-50 border-blue-300"
                        : "bg-white border-gray-200 hover:bg-gray-50"
                    )}
                  >
                    {/* Vehicle ID and Severity Badge */}
                    <div className="flex items-center justify-between mb-2 gap-2">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="font-mono font-bold text-sm text-gray-900 break-words">
                          {group.vehicleDisplayId}
                        </span>
                      </div>
                      <Badge
                        className={cn(
                          "text-xs font-bold px-2 py-0.5 rounded-full border flex-shrink-0",
                          severityClass
                        )}
                      >
                        {group.highestSeverity}
                      </Badge>
                    </div>

                    {/* Description */}
                    <div className="text-xs text-gray-600 mb-2 break-words">
                      {ruleDescription}
                    </div>

                    {/* Timestamp and Icons */}
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        {formatDate(group.lastUpdated)}
                      </span>
                      <div className="flex items-center gap-2">
                        <Mail className="w-3.5 h-3.5 text-gray-400" />
                        <ChevronDown
                          className={cn(
                            "w-3.5 h-3.5 text-gray-400 transition-transform",
                            isExpanded && "transform rotate-180"
                          )}
                        />
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      <div className="p-3 border-t border-gray-200 flex items-center justify-between bg-white">
        <Button
          size="sm"
          className="h-8 px-3 text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded"
        >
          1 Respond
        </Button>
        <div className="flex items-center gap-2">
          <button className="p-1.5 text-gray-400 hover:text-gray-600 rounded transition-colors">
            <Download className="w-4 h-4" />
          </button>
          <button className="p-1.5 text-gray-400 hover:text-gray-600 rounded transition-colors">
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
