// Incident panel showing alert evidence and actions with enhanced display

import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useTheme } from "../contexts/ThemeContext";
import type { Alert, Action, Severity } from "../types";

interface IncidentPanelProps {
  alert: Alert | null;
}

export function IncidentPanel({ alert }: IncidentPanelProps) {
  const { theme } = useTheme();
  const [actions, setActions] = useState<Action[]>([]);
  const [loadingActions, setLoadingActions] = useState(false);

  useEffect(() => {
    if (!alert) {
      setActions([]);
      return;
    }

    async function fetchActions() {
      try {
        setLoadingActions(true);
        const vehicleActions = await api.getActions(alert.vehicle_id);
        // Get last 5 actions
        const sortedActions = vehicleActions
          .sort(
            (a, b) =>
              new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
          .slice(0, 5);
        setActions(sortedActions);
      } catch (error) {
        console.error("Failed to fetch actions:", error);
      } finally {
        setLoadingActions(false);
      }
    }

    fetchActions();
  }, [alert]);

  if (!alert) {
    return (
      <div 
        style={{ 
          padding: "32px 16px", 
          color: theme.colors.textMuted, 
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <div style={{ fontSize: "24px", opacity: 0.5 }}>📋</div>
        <div style={{ fontSize: "13px" }}>Select an alert to view incident details</div>
      </div>
    );
  }

  const getSeverityConfig = (severity: Severity) => {
    switch (severity) {
      case "CRITICAL":
        return { color: theme.colors.critical, bg: theme.colors.criticalMuted };
      case "WARNING":
        return { color: theme.colors.warning, bg: theme.colors.warningMuted };
      case "INFO":
        return { color: theme.colors.info, bg: theme.colors.infoMuted };
      default:
        return { color: theme.colors.textMuted, bg: theme.colors.surfaceSecondary };
    }
  };

  const severityConfig = getSeverityConfig(alert.severity);
  const features = alert.anomaly_payload.features || {};
  const thresholds = alert.anomaly_payload.thresholds || {};

  // Format feature values for display
  const formatValue = (key: string, value: any): string => {
    if (typeof value === "number") {
      // Format based on key name
      if (key.includes("acceleration") || key.includes("speed") || key.includes("velocity")) {
        return `${value.toFixed(2)} m/s${key.includes("acceleration") ? "²" : ""}`;
      }
      if (key.includes("displacement") || key.includes("distance") || key.includes("jump")) {
        return `${value.toFixed(2)} m`;
      }
      if (key.includes("probability") || key.includes("change")) {
        return `${(value * 100).toFixed(1)}%`;
      }
      return value.toFixed(3);
    }
    return String(value);
  };

  const InfoSection = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div style={{ marginBottom: "16px" }}>
      <div
        style={{
          fontSize: "10px",
          color: theme.colors.textMuted,
          marginBottom: "8px",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          fontWeight: 600,
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );

  return (
    <div style={{ padding: "16px", overflowY: "auto", maxHeight: "400px" }}>
      {/* Header */}
      <h2 style={{ 
        margin: "0 0 16px 0", 
        fontSize: "14px", 
        fontWeight: 700, 
        color: theme.colors.textSecondary,
        letterSpacing: "0.5px",
      }}>
        INCIDENT DETAILS
      </h2>

      {/* Incident ID */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            fontSize: "18px",
            fontWeight: 700,
            fontFamily: theme.fonts.mono,
            color: theme.colors.text,
            marginBottom: "4px",
          }}
        >
          {alert.incident_id || `INC-${alert.id.slice(0, 5).toUpperCase()}`}
        </div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span
            style={{
              padding: "3px 8px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 700,
              backgroundColor: severityConfig.bg,
              color: severityConfig.color,
            }}
          >
            {alert.severity}
          </span>
          <span
            style={{
              padding: "3px 8px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: 
                alert.status === "OPEN" ? theme.colors.errorMuted :
                alert.status === "ACKNOWLEDGED" ? theme.colors.warningMuted :
                theme.colors.successMuted,
              color: 
                alert.status === "OPEN" ? theme.colors.error :
                alert.status === "ACKNOWLEDGED" ? theme.colors.warning :
                theme.colors.success,
            }}
          >
            {alert.status}
          </span>
        </div>
      </div>

      {/* Rule */}
      <InfoSection title="Detection Rule">
        <div style={{ 
          fontSize: "13px", 
          fontWeight: 600, 
          color: theme.colors.text 
        }}>
          {alert.rule_display_name || alert.rule_name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
        </div>
      </InfoSection>

      {/* Vehicle */}
      <InfoSection title="Vehicle">
        <div style={{ 
          fontSize: "13px", 
          fontWeight: 600, 
          color: theme.colors.text,
          fontFamily: theme.fonts.mono,
        }}>
          {alert.vehicle_display_id || alert.vehicle_id}
        </div>
      </InfoSection>

      {/* Scene Info */}
      <InfoSection title="Context">
        <div 
          style={{ 
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
            fontSize: "12px", 
            color: theme.colors.text,
            padding: "8px",
            backgroundColor: theme.colors.surfaceSecondary,
            borderRadius: "6px",
          }}
        >
          <div>
            <span style={{ color: theme.colors.textMuted }}>Scene: </span>
            <span style={{ fontFamily: theme.fonts.mono }}>
              {alert.scene_display_id || alert.scene_id}
            </span>
          </div>
          <div>
            <span style={{ color: theme.colors.textMuted }}>Frame: </span>
            <span style={{ fontFamily: theme.fonts.mono }}>{alert.frame_index}</span>
          </div>
        </div>
      </InfoSection>

      {/* Event Times */}
      <InfoSection title="Timeline">
        <div 
          style={{ 
            fontSize: "11px", 
            color: theme.colors.textSecondary,
            display: "flex",
            flexDirection: "column",
            gap: "4px",
          }}
        >
          <div>
            <span style={{ color: theme.colors.textMuted }}>First seen: </span>
            {new Date(alert.first_seen_event_time).toLocaleString()}
          </div>
          <div>
            <span style={{ color: theme.colors.textMuted }}>Last seen: </span>
            {new Date(alert.last_seen_event_time).toLocaleString()}
          </div>
        </div>
      </InfoSection>

      {/* Features (Evidence) */}
      {Object.keys(features).length > 0 && (
        <InfoSection title="Evidence">
          <div
            style={{
              backgroundColor: theme.colors.surfaceSecondary,
              padding: "10px",
              borderRadius: "6px",
              fontSize: "11px",
              fontFamily: theme.fonts.mono,
            }}
          >
            {Object.entries(features).map(([key, value]) => (
              <div 
                key={key} 
                style={{ 
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "6px",
                  paddingBottom: "6px",
                  borderBottom: `1px solid ${theme.colors.borderSubtle}`,
                }}
              >
                <span style={{ color: theme.colors.textSecondary }}>
                  {key.replace(/_/g, " ")}
                </span>
                <span style={{ color: theme.colors.text, fontWeight: 600 }}>
                  {formatValue(key, value)}
                </span>
              </div>
            ))}
          </div>
        </InfoSection>
      )}

      {/* Thresholds */}
      {Object.keys(thresholds).length > 0 && (
        <InfoSection title="Thresholds">
          <div
            style={{
              backgroundColor: theme.colors.surfaceSecondary,
              padding: "10px",
              borderRadius: "6px",
              fontSize: "11px",
              fontFamily: theme.fonts.mono,
            }}
          >
            {Object.entries(thresholds).map(([key, value]) => (
              <div 
                key={key} 
                style={{ 
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "4px",
                }}
              >
                <span style={{ color: theme.colors.textMuted }}>
                  {key.replace(/_/g, " ")}
                </span>
                <span style={{ color: theme.colors.textSecondary }}>
                  {formatValue(key, value)}
                </span>
              </div>
            ))}
          </div>
        </InfoSection>
      )}

      {/* Action History */}
      <InfoSection title="Action History">
        {loadingActions ? (
          <div style={{ fontSize: "11px", color: theme.colors.textMuted }}>Loading...</div>
        ) : actions.length === 0 ? (
          <div style={{ fontSize: "11px", color: theme.colors.textMuted }}>No actions recorded</div>
        ) : (
          <div
            style={{
              backgroundColor: theme.colors.surfaceSecondary,
              borderRadius: "6px",
              overflow: "hidden",
            }}
          >
            {actions.map((action, index) => (
              <div
                key={action.id}
                style={{
                  padding: "8px 10px",
                  borderBottom: index < actions.length - 1 
                    ? `1px solid ${theme.colors.borderSubtle}` 
                    : "none",
                }}
              >
                <div style={{ 
                  fontSize: "11px",
                  fontWeight: 600, 
                  color: theme.colors.text,
                  marginBottom: "2px",
                }}>
                  {action.action_type.replace(/_/g, " ")}
                </div>
                <div style={{ 
                  fontSize: "10px",
                  color: theme.colors.textMuted,
                  display: "flex",
                  justifyContent: "space-between",
                }}>
                  <span>by {action.actor}</span>
                  <span>{new Date(action.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </InfoSection>
    </div>
  );
}

