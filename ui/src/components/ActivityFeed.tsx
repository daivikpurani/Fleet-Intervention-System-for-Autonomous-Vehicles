// Activity feed showing chronological event timeline

import { useEffect, useState, useRef } from "react";
import { useTheme } from "../contexts/ThemeContext";
import type { Alert, Action, Vehicle } from "../types";

interface ActivityItem {
  id: string;
  type: "alert_created" | "alert_acknowledged" | "alert_resolved" | "vehicle_state_change";
  timestamp: Date;
  title: string;
  description: string;
  severity?: "CRITICAL" | "WARNING" | "INFO";
  vehicleId?: string;
  incidentId?: string;
}

interface ActivityFeedProps {
  alerts: Alert[];
  maxItems?: number;
}

export function ActivityFeed({ alerts, maxItems = 10 }: ActivityFeedProps) {
  const { theme } = useTheme();
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const prevAlertsRef = useRef<Alert[]>([]);

  // Convert alerts to activity items and detect changes
  useEffect(() => {
    const newActivities: ActivityItem[] = [];
    const prevAlertIds = new Set(prevAlertsRef.current.map(a => a.id));
    const prevAlertStatus = new Map(prevAlertsRef.current.map(a => [a.id, a.status]));

    alerts.forEach((alert) => {
      // Check if this is a new alert
      if (!prevAlertIds.has(alert.id)) {
        newActivities.push({
          id: `${alert.id}-created`,
          type: "alert_created",
          timestamp: new Date(alert.created_at),
          title: `New Incident: ${alert.incident_id || alert.id.slice(0, 8)}`,
          description: `${alert.rule_display_name || alert.rule_name} on ${alert.vehicle_display_id || alert.vehicle_id}`,
          severity: alert.severity,
          vehicleId: alert.vehicle_id,
          incidentId: alert.incident_id || undefined,
        });
      } else {
        // Check for status changes
        const prevStatus = prevAlertStatus.get(alert.id);
        if (prevStatus && prevStatus !== alert.status) {
          if (alert.status === "ACKNOWLEDGED") {
            newActivities.push({
              id: `${alert.id}-ack-${Date.now()}`,
              type: "alert_acknowledged",
              timestamp: new Date(alert.updated_at),
              title: `Incident Acknowledged`,
              description: `${alert.incident_id || alert.id.slice(0, 8)} acknowledged`,
              severity: alert.severity,
              vehicleId: alert.vehicle_id,
              incidentId: alert.incident_id || undefined,
            });
          } else if (alert.status === "RESOLVED") {
            newActivities.push({
              id: `${alert.id}-resolved-${Date.now()}`,
              type: "alert_resolved",
              timestamp: new Date(alert.updated_at),
              title: `Incident Resolved`,
              description: `${alert.incident_id || alert.id.slice(0, 8)} resolved`,
              severity: alert.severity,
              vehicleId: alert.vehicle_id,
              incidentId: alert.incident_id || undefined,
            });
          }
        }
      }
    });

    // Add new activities to the list
    if (newActivities.length > 0) {
      setActivities(prev => {
        const combined = [...newActivities, ...prev];
        // Sort by timestamp descending and limit
        return combined
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
          .slice(0, maxItems);
      });
    }

    // Update ref for next comparison
    prevAlertsRef.current = alerts;
  }, [alerts, maxItems]);

  const getActivityIcon = (type: ActivityItem["type"]) => {
    switch (type) {
      case "alert_created":
        return "🔔";
      case "alert_acknowledged":
        return "👁️";
      case "alert_resolved":
        return "✓";
      case "vehicle_state_change":
        return "🚗";
      default:
        return "•";
    }
  };

  const getActivityColor = (activity: ActivityItem) => {
    if (activity.type === "alert_resolved") return theme.colors.success;
    if (activity.type === "alert_acknowledged") return theme.colors.warning;
    if (activity.severity === "CRITICAL") return theme.colors.critical;
    if (activity.severity === "WARNING") return theme.colors.warning;
    return theme.colors.info;
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: theme.colors.surface,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: `1px solid ${theme.colors.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontSize: "12px",
            fontWeight: 700,
            color: theme.colors.textSecondary,
            letterSpacing: "0.5px",
          }}
        >
          ACTIVITY
        </span>
        <span
          style={{
            fontSize: "10px",
            color: theme.colors.textMuted,
          }}
        >
          Last {maxItems} events
        </span>
      </div>

      {/* Activity List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px",
        }}
      >
        {activities.length === 0 ? (
          <div
            style={{
              padding: "20px",
              textAlign: "center",
              color: theme.colors.textMuted,
              fontSize: "12px",
            }}
          >
            No recent activity
          </div>
        ) : (
          activities.map((activity, index) => (
            <div
              key={activity.id}
              style={{
                display: "flex",
                gap: "10px",
                padding: "8px",
                marginBottom: "4px",
                borderRadius: "6px",
                backgroundColor: index === 0 ? theme.colors.surfaceSecondary : "transparent",
                animation: index === 0 ? "fadeIn 0.3s ease-out" : undefined,
              }}
            >
              {/* Timeline dot */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  paddingTop: "2px",
                }}
              >
                <span
                  style={{
                    width: "20px",
                    height: "20px",
                    borderRadius: "50%",
                    backgroundColor: getActivityColor(activity) + "22",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "10px",
                  }}
                >
                  {getActivityIcon(activity.type)}
                </span>
                {index < activities.length - 1 && (
                  <div
                    style={{
                      width: "2px",
                      flex: 1,
                      backgroundColor: theme.colors.borderSubtle,
                      marginTop: "4px",
                    }}
                  />
                )}
              </div>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: "8px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      color: theme.colors.text,
                    }}
                  >
                    {activity.title}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontFamily: theme.fonts.mono,
                      color: theme.colors.textMuted,
                      flexShrink: 0,
                    }}
                  >
                    {formatTime(activity.timestamp)}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: "10px",
                    color: theme.colors.textSecondary,
                    marginTop: "2px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {activity.description}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* CSS for animations */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

