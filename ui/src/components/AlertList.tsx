// Alert list component with filtering

import { useMemo, useEffect, useRef } from "react";
import type { Alert, AlertStatus, Severity } from "../types";
import { useAlerts } from "../hooks/useAlerts";
import { useTheme } from "../contexts/ThemeContext";

interface AlertListProps {
  onAlertClick: (alert: Alert) => void;
  demoMode?: boolean;
}

export function AlertList({ onAlertClick, demoMode = false }: AlertListProps) {
  const { theme } = useTheme();
  const {
    alerts,
    selectedAlert,
    filters,
    updateFilters,
    selectAlert,
    loading,
    error,
  } = useAlerts();

  // Store the latest onAlertClick callback in a ref to avoid unnecessary effect re-runs.
  // This prevents the effect from running when the parent recreates the callback function
  // (which happens on every render if not memoized with useCallback).
  const onAlertClickRef = useRef(onAlertClick);
  useEffect(() => {
    onAlertClickRef.current = onAlertClick;
  }, [onAlertClick]);

  // Demo mode: auto-select first CRITICAL alert
  useEffect(() => {
    if (demoMode && alerts.length > 0 && !selectedAlert) {
      const criticalAlert = alerts.find((a) => a.severity === "CRITICAL");
      if (criticalAlert) {
        selectAlert(criticalAlert.id);
        onAlertClickRef.current(criticalAlert);
      }
    }
  }, [demoMode, alerts, selectedAlert, selectAlert]);

  const handleStatusChange = (status: AlertStatus | "") => {
    updateFilters({ status: status || undefined });
  };

  const handleSeverityChange = (severity: Severity | "") => {
    updateFilters({ severity: severity || undefined });
  };

  const handleVehicleIdChange = (vehicleId: string) => {
    updateFilters({ vehicleId: vehicleId || undefined });
  };

  const handleAlertClick = (alert: Alert) => {
    selectAlert(alert.id);
    onAlertClick(alert);
  };

  const getSeverityColor = (severity: Severity): string => {
    switch (severity) {
      case "CRITICAL":
        return "#d32f2f";
      case "WARNING":
        return "#ff6b35";
      case "INFO":
        return "#2196f3";
      default:
        return "#888";
    }
  };

  const getStatusColor = (status: AlertStatus): string => {
    switch (status) {
      case "OPEN":
        return "#d32f2f";
      case "ACKNOWLEDGED":
        return "#ff9800";
      case "RESOLVED":
        return "#4caf50";
      default:
        return "#888";
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "16px", borderBottom: `1px solid ${theme.colors.border}` }}>
        <h2 style={{ margin: "0 0 16px 0", fontSize: "18px", color: theme.colors.text }}>
          Alerts
        </h2>

        {/* Filters */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div>
            <label
              style={{
                display: "block",
                marginBottom: "4px",
                fontSize: "12px",
                color: theme.colors.textSecondary,
              }}
            >
              Status
            </label>
            <select
              value={filters.status || ""}
              onChange={(e) => handleStatusChange(e.target.value as AlertStatus | "")}
              style={{
                width: "100%",
                padding: "4px",
                backgroundColor: theme.colors.surface,
                color: theme.colors.text,
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "4px",
              }}
            >
              <option value="">All</option>
              <option value="OPEN">OPEN</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>

          <div>
            <label
              style={{
                display: "block",
                marginBottom: "4px",
                fontSize: "12px",
                color: theme.colors.textSecondary,
              }}
            >
              Severity
            </label>
            <select
              value={filters.severity || ""}
              onChange={(e) => handleSeverityChange(e.target.value as Severity | "")}
              style={{
                width: "100%",
                padding: "4px",
                backgroundColor: theme.colors.surface,
                color: theme.colors.text,
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "4px",
              }}
            >
              <option value="">All</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>
          </div>

          <div>
            <label
              style={{
                display: "block",
                marginBottom: "4px",
                fontSize: "12px",
                color: theme.colors.textSecondary,
              }}
            >
              Vehicle ID
            </label>
            <input
              type="text"
              value={filters.vehicleId || ""}
              onChange={(e) => handleVehicleIdChange(e.target.value)}
              placeholder="Search vehicle..."
              style={{
                width: "100%",
                padding: "4px",
                backgroundColor: theme.colors.surface,
                color: theme.colors.text,
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "4px",
              }}
            />
          </div>
        </div>
      </div>

      {/* Alert List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px",
        }}
      >
        {loading ? (
          <div style={{ padding: "16px", textAlign: "center", color: theme.colors.textMuted }}>
            Loading alerts...
          </div>
        ) : error ? (
          <div style={{ padding: "16px", textAlign: "center", color: theme.colors.error }}>
            Error: {error}
          </div>
        ) : alerts.length === 0 ? (
          <div style={{ padding: "16px", textAlign: "center", color: theme.colors.textMuted }}>
            No alerts found
          </div>
        ) : (
          alerts.map((alert) => {
            const isSelected = selectedAlert?.id === alert.id;
            return (
              <div
                key={alert.id}
                onClick={() => handleAlertClick(alert)}
                style={{
                  padding: "12px",
                  marginBottom: "8px",
                  border: `2px solid ${isSelected ? theme.colors.primary : theme.colors.border}`,
                  borderRadius: "4px",
                  cursor: "pointer",
                  backgroundColor: isSelected ? theme.colors.selected : theme.colors.surface,
                  transition: "all 0.2s",
                  color: theme.colors.text,
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = theme.colors.hover;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = theme.colors.surface;
                  }
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: "bold",
                    }}
                  >
                    {alert.vehicle_id}
                  </div>
                  <div
                    style={{
                      padding: "2px 8px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: "bold",
                      backgroundColor: getSeverityColor(alert.severity),
                      color: "#fff",
                    }}
                  >
                    {alert.severity}
                  </div>
                </div>

                <div
                  style={{
                    fontSize: "12px",
                    color: theme.colors.textSecondary,
                    marginBottom: "4px",
                  }}
                >
                  {alert.rule_name}
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "11px",
                    color: theme.colors.textMuted,
                  }}
                >
                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: "3px",
                      backgroundColor: getStatusColor(alert.status),
                      color: "#fff",
                      fontSize: "10px",
                    }}
                  >
                    {alert.status}
                  </span>
                  <span>
                    {new Date(alert.last_seen_event_time).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
