// Alert list component with incident numbers and professional styling

import { useMemo, useEffect, useRef } from "react";
import type { Alert, AlertStatus, Severity } from "../types";
import { useAlerts } from "../hooks/useAlerts";
import { useTheme } from "../contexts/ThemeContext";

interface AlertListProps {
  onAlertClick: (alert: Alert) => void;
  demoMode?: boolean;
}

// Helper to get relative time string
function getRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  return date.toLocaleDateString();
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

  // Store the latest onAlertClick callback in a ref
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

  const getSeverityConfig = (severity: Severity) => {
    switch (severity) {
      case "CRITICAL":
        return { 
          color: theme.colors.critical, 
          bg: theme.colors.criticalMuted,
          label: "CRIT"
        };
      case "WARNING":
        return { 
          color: theme.colors.warning, 
          bg: theme.colors.warningMuted,
          label: "WARN"
        };
      case "INFO":
        return { 
          color: theme.colors.info, 
          bg: theme.colors.infoMuted,
          label: "INFO"
        };
      default:
        return { color: theme.colors.textMuted, bg: theme.colors.surfaceSecondary, label: "?" };
    }
  };

  const getStatusConfig = (status: AlertStatus) => {
    switch (status) {
      case "OPEN":
        return { color: theme.colors.error, label: "OPEN" };
      case "ACKNOWLEDGED":
        return { color: theme.colors.warning, label: "ACK" };
      case "RESOLVED":
        return { color: theme.colors.success, label: "RESOLVED" };
      default:
        return { color: theme.colors.textMuted, label: "?" };
    }
  };

  // Count alerts by severity
  const alertCounts = useMemo(() => {
    const openAlerts = alerts.filter((a) => a.status === "OPEN");
    return {
      critical: openAlerts.filter((a) => a.severity === "CRITICAL").length,
      warning: openAlerts.filter((a) => a.severity === "WARNING").length,
      info: openAlerts.filter((a) => a.severity === "INFO").length,
      total: openAlerts.length,
    };
  }, [alerts]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "16px", borderBottom: `1px solid ${theme.colors.border}` }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <h2 style={{ 
            margin: 0, 
            fontSize: "14px", 
            fontWeight: 700, 
            color: theme.colors.text,
            letterSpacing: "0.5px",
          }}>
            ACTIVE INCIDENTS
          </h2>
          <span
            style={{
              fontSize: "12px",
              fontFamily: theme.fonts.mono,
              fontWeight: 600,
              color: alertCounts.total > 0 ? theme.colors.warning : theme.colors.textMuted,
              padding: "2px 8px",
              backgroundColor: alertCounts.total > 0 ? theme.colors.warningMuted : theme.colors.surfaceSecondary,
              borderRadius: "4px",
            }}
          >
            {alertCounts.total}
          </span>
        </div>

        {/* Quick Stats */}
        {alertCounts.total > 0 && (
          <div style={{ 
            display: "flex", 
            gap: "8px", 
            marginBottom: "12px",
            flexWrap: "wrap",
          }}>
            {alertCounts.critical > 0 && (
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  backgroundColor: theme.colors.criticalMuted,
                  color: theme.colors.critical,
                }}
              >
                {alertCounts.critical} Critical
              </span>
            )}
            {alertCounts.warning > 0 && (
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  backgroundColor: theme.colors.warningMuted,
                  color: theme.colors.warning,
                }}
              >
                {alertCounts.warning} Warning
              </span>
            )}
            {alertCounts.info > 0 && (
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "4px",
                  backgroundColor: theme.colors.infoMuted,
                  color: theme.colors.info,
                }}
              >
                {alertCounts.info} Info
              </span>
            )}
          </div>
        )}

        {/* Filters */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", gap: "8px" }}>
            <select
              value={filters.status || ""}
              onChange={(e) => handleStatusChange(e.target.value as AlertStatus | "")}
              style={{
                flex: 1,
                padding: "6px 8px",
                backgroundColor: theme.colors.surfaceSecondary,
                color: theme.colors.text,
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "6px",
                fontSize: "12px",
              }}
            >
              <option value="">All Status</option>
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="RESOLVED">Resolved</option>
            </select>

            <select
              value={filters.severity || ""}
              onChange={(e) => handleSeverityChange(e.target.value as Severity | "")}
              style={{
                flex: 1,
                padding: "6px 8px",
                backgroundColor: theme.colors.surfaceSecondary,
                color: theme.colors.text,
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "6px",
                fontSize: "12px",
              }}
            >
              <option value="">All Severity</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
            </select>
          </div>

          <input
            type="text"
            value={filters.vehicleId || ""}
            onChange={(e) => handleVehicleIdChange(e.target.value)}
            placeholder="Search vehicle..."
            style={{
              width: "100%",
              padding: "6px 10px",
              backgroundColor: theme.colors.surfaceSecondary,
              color: theme.colors.text,
              border: `1px solid ${theme.colors.border}`,
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
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
          <div style={{ padding: "20px", textAlign: "center", color: theme.colors.textMuted }}>
            Loading incidents...
          </div>
        ) : error ? (
          <div style={{ padding: "20px", textAlign: "center", color: theme.colors.error }}>
            Error: {error}
          </div>
        ) : alerts.length === 0 ? (
          <div style={{ 
            padding: "40px 20px", 
            textAlign: "center", 
            color: theme.colors.textMuted,
          }}>
            <div style={{ fontSize: "24px", marginBottom: "8px" }}>✓</div>
            <div style={{ fontSize: "13px" }}>No active incidents</div>
          </div>
        ) : (
          alerts.map((alert, index) => {
            const isSelected = selectedAlert?.id === alert.id;
            const severityConfig = getSeverityConfig(alert.severity);
            const statusConfig = getStatusConfig(alert.status);
            const isNew = index === 0 && Date.now() - new Date(alert.created_at).getTime() < 5000;

            return (
              <div
                key={alert.id}
                onClick={() => handleAlertClick(alert)}
                style={{
                  padding: "12px",
                  marginBottom: "8px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  backgroundColor: isSelected 
                    ? theme.colors.selected 
                    : theme.colors.surfaceSecondary,
                  border: `2px solid ${isSelected 
                    ? theme.colors.primary 
                    : alert.severity === "CRITICAL" && alert.status === "OPEN"
                      ? theme.colors.critical
                      : theme.colors.borderSubtle}`,
                  transition: "all 0.2s",
                  animation: isNew ? "slideIn 0.3s ease-out" : undefined,
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = theme.colors.hover;
                    e.currentTarget.style.borderColor = theme.colors.border;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = theme.colors.surfaceSecondary;
                    e.currentTarget.style.borderColor = 
                      alert.severity === "CRITICAL" && alert.status === "OPEN"
                        ? theme.colors.critical
                        : theme.colors.borderSubtle;
                  }
                }}
              >
                {/* Top Row: Incident ID & Severity */}
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
                      fontFamily: theme.fonts.mono,
                      fontSize: "13px",
                      fontWeight: 700,
                      color: theme.colors.text,
                    }}
                  >
                    {alert.incident_id || `INC-${alert.id.slice(0, 5).toUpperCase()}`}
                  </div>
                  <div
                    style={{
                      padding: "2px 8px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: 700,
                      backgroundColor: severityConfig.bg,
                      color: severityConfig.color,
                      letterSpacing: "0.5px",
                    }}
                  >
                    {severityConfig.label}
                  </div>
                </div>

                {/* Vehicle ID */}
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: theme.colors.text,
                    marginBottom: "4px",
                  }}
                >
                  {alert.vehicle_display_id || alert.vehicle_id}
                </div>

                {/* Rule Name */}
                <div
                  style={{
                    fontSize: "11px",
                    color: theme.colors.textSecondary,
                    marginBottom: "8px",
                  }}
                >
                  {alert.rule_display_name || alert.rule_name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                </div>

                {/* Bottom Row: Status & Time */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "10px",
                  }}
                >
                  <span
                    style={{
                      padding: "2px 6px",
                      borderRadius: "3px",
                      fontWeight: 600,
                      backgroundColor: 
                        alert.status === "OPEN" ? theme.colors.errorMuted :
                        alert.status === "ACKNOWLEDGED" ? theme.colors.warningMuted :
                        theme.colors.successMuted,
                      color: statusConfig.color,
                    }}
                  >
                    {statusConfig.label}
                  </span>
                  <span style={{ color: theme.colors.textMuted, fontFamily: theme.fonts.mono }}>
                    {getRelativeTime(alert.last_seen_event_time)}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* CSS for animations */}
      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}
