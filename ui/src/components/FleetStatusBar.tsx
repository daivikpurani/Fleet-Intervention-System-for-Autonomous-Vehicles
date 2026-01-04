// Fleet status bar showing real-time fleet statistics

import { useMemo } from "react";
import { useTheme } from "../contexts/ThemeContext";
import type { Vehicle, Alert, Severity } from "../types";

interface FleetStatusBarProps {
  vehicles: Vehicle[];
  alerts: Alert[];
  isConnected: boolean;
}

export function FleetStatusBar({ vehicles, alerts, isConnected }: FleetStatusBarProps) {
  const { theme } = useTheme();

  const stats = useMemo(() => {
    const openAlerts = alerts.filter((a) => a.status === "OPEN");
    const criticalCount = openAlerts.filter((a) => a.severity === "CRITICAL").length;
    const warningCount = openAlerts.filter((a) => a.severity === "WARNING").length;
    const infoCount = openAlerts.filter((a) => a.severity === "INFO").length;
    
    const normalVehicles = vehicles.filter((v) => v.state === "NORMAL").length;
    const alertingVehicles = vehicles.filter((v) => v.state === "ALERTING").length;
    const interventionVehicles = vehicles.filter((v) => v.state === "UNDER_INTERVENTION").length;
    
    const egoVehicles = vehicles.filter((v) => v.vehicle_type === "Autonomous Vehicle").length;
    const trackedVehicles = vehicles.filter((v) => v.vehicle_type === "Tracked Vehicle").length;

    return {
      totalVehicles: vehicles.length,
      egoVehicles,
      trackedVehicles,
      normalVehicles,
      alertingVehicles,
      interventionVehicles,
      totalOpenAlerts: openAlerts.length,
      criticalCount,
      warningCount,
      infoCount,
    };
  }, [vehicles, alerts]);

  const StatItem = ({ 
    label, 
    value, 
    color,
    pulse = false,
  }: { 
    label: string; 
    value: number; 
    color?: string;
    pulse?: boolean;
  }) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 12px",
        backgroundColor: theme.colors.surfaceSecondary,
        borderRadius: "6px",
        border: `1px solid ${theme.colors.borderSubtle}`,
      }}
    >
      <span
        style={{
          fontSize: "11px",
          fontWeight: 500,
          color: theme.colors.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: "16px",
          fontWeight: 700,
          fontFamily: theme.fonts.mono,
          color: color || theme.colors.text,
          animation: pulse ? "pulse 2s infinite" : undefined,
        }}
      >
        {value}
      </span>
    </div>
  );

  const currentTime = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 16px",
        backgroundColor: theme.colors.surface,
        borderBottom: `1px solid ${theme.colors.border}`,
        gap: "16px",
        flexWrap: "wrap",
      }}
    >
      {/* Left: Fleet Stats */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span
          style={{
            fontSize: "12px",
            fontWeight: 600,
            color: theme.colors.textSecondary,
            marginRight: "4px",
          }}
        >
          FLEET
        </span>
        <StatItem label="Total" value={stats.totalVehicles} />
        <StatItem label="AV" value={stats.egoVehicles} color={theme.colors.primary} />
        <StatItem label="Nominal" value={stats.normalVehicles} color={theme.colors.success} />
        <StatItem 
          label="Alerting" 
          value={stats.alertingVehicles} 
          color={stats.alertingVehicles > 0 ? theme.colors.warning : theme.colors.textMuted} 
        />
        {stats.interventionVehicles > 0 && (
          <StatItem 
            label="Intervention" 
            value={stats.interventionVehicles} 
            color={theme.colors.error}
            pulse 
          />
        )}
      </div>

      {/* Center: Alert Stats */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span
          style={{
            fontSize: "12px",
            fontWeight: 600,
            color: theme.colors.textSecondary,
            marginRight: "4px",
          }}
        >
          ALERTS
        </span>
        {stats.criticalCount > 0 && (
          <StatItem 
            label="Critical" 
            value={stats.criticalCount} 
            color={theme.colors.critical}
            pulse
          />
        )}
        <StatItem 
          label="Warning" 
          value={stats.warningCount} 
          color={stats.warningCount > 0 ? theme.colors.warning : theme.colors.textMuted} 
        />
        <StatItem 
          label="Info" 
          value={stats.infoCount} 
          color={theme.colors.info} 
        />
      </div>

      {/* Right: Status & Time */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Connection Status */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "4px 10px",
            borderRadius: "4px",
            backgroundColor: isConnected 
              ? theme.colors.successMuted 
              : theme.colors.errorMuted,
          }}
        >
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: isConnected ? theme.colors.success : theme.colors.error,
              animation: isConnected ? undefined : "pulse 1s infinite",
            }}
          />
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              color: isConnected ? theme.colors.success : theme.colors.error,
            }}
          >
            {isConnected ? "LIVE" : "OFFLINE"}
          </span>
        </div>

        {/* Clock */}
        <div
          style={{
            fontFamily: theme.fonts.mono,
            fontSize: "14px",
            fontWeight: 600,
            color: theme.colors.textSecondary,
            padding: "4px 8px",
            backgroundColor: theme.colors.surfaceSecondary,
            borderRadius: "4px",
          }}
        >
          {currentTime}
        </div>
      </div>
    </div>
  );
}

