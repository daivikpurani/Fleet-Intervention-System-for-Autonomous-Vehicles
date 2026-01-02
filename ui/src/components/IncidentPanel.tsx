// Incident panel showing alert evidence and actions

import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Alert, Action, Severity } from "../types";

interface IncidentPanelProps {
  alert: Alert | null;
}

export function IncidentPanel({ alert }: IncidentPanelProps) {
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
      <div style={{ padding: "16px", color: "#888", textAlign: "center" }}>
        Select an alert to view incident details
      </div>
    );
  }

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

  const features = alert.anomaly_payload.features || {};
  const thresholds = alert.anomaly_payload.thresholds || {};

  return (
    <div style={{ padding: "16px", overflowY: "auto", height: "100%" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: "18px" }}>Incident Details</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Rule Name */}
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
            Rule Name
          </div>
          <div style={{ fontSize: "14px", fontWeight: "bold" }}>
            {alert.rule_name}
          </div>
        </div>

        {/* Severity */}
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
            Severity
          </div>
          <div
            style={{
              display: "inline-block",
              padding: "4px 12px",
              borderRadius: "4px",
              fontSize: "12px",
              fontWeight: "bold",
              backgroundColor: getSeverityColor(alert.severity),
              color: "#fff",
            }}
          >
            {alert.severity}
          </div>
        </div>

        {/* Event Times */}
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
            Event Times
          </div>
          <div style={{ fontSize: "12px" }}>
            <div>First seen: {new Date(alert.first_seen_event_time).toLocaleString()}</div>
            <div>Last seen: {new Date(alert.last_seen_event_time).toLocaleString()}</div>
          </div>
        </div>

        {/* Scene Info */}
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
            Scene Info
          </div>
          <div style={{ fontSize: "12px" }}>
            Scene ID: {alert.scene_id}
            <br />
            Frame Index: {alert.frame_index}
          </div>
        </div>

        {/* Status */}
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>
            Status
          </div>
          <div style={{ fontSize: "14px", fontWeight: "bold" }}>{alert.status}</div>
        </div>

        {/* Features */}
        {Object.keys(features).length > 0 && (
          <div>
            <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
              Features
            </div>
            <div
              style={{
                backgroundColor: "#f5f5f5",
                padding: "8px",
                borderRadius: "4px",
                fontSize: "12px",
              }}
            >
              {Object.entries(features).map(([key, value]) => (
                <div key={key} style={{ marginBottom: "4px" }}>
                  <strong>{key}:</strong> {String(value)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Thresholds */}
        {Object.keys(thresholds).length > 0 && (
          <div>
            <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
              Thresholds
            </div>
            <div
              style={{
                backgroundColor: "#f5f5f5",
                padding: "8px",
                borderRadius: "4px",
                fontSize: "12px",
              }}
            >
              {Object.entries(thresholds).map(([key, value]) => (
                <div key={key} style={{ marginBottom: "4px" }}>
                  <strong>{key}:</strong> {String(value)}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Last 5 Actions */}
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
            Last 5 Actions
          </div>
          {loadingActions ? (
            <div style={{ fontSize: "12px", color: "#888" }}>Loading...</div>
          ) : actions.length === 0 ? (
            <div style={{ fontSize: "12px", color: "#888" }}>No actions yet</div>
          ) : (
            <div
              style={{
                backgroundColor: "#f5f5f5",
                padding: "8px",
                borderRadius: "4px",
                fontSize: "12px",
              }}
            >
              {actions.map((action) => (
                <div
                  key={action.id}
                  style={{
                    marginBottom: "8px",
                    paddingBottom: "8px",
                    borderBottom: "1px solid #ddd",
                  }}
                >
                  <div style={{ fontWeight: "bold", marginBottom: "4px" }}>
                    {action.action_type}
                  </div>
                  <div style={{ color: "#666", fontSize: "11px" }}>
                    Actor: {action.actor}
                    <br />
                    {new Date(action.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
