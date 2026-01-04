// Vehicle detail panel component with enhanced display

import type { Vehicle, VehicleState } from "../types";
import { useTheme } from "../contexts/ThemeContext";

interface VehicleDetailProps {
  vehicle: Vehicle | null;
}

export function VehicleDetail({ vehicle }: VehicleDetailProps) {
  const { theme } = useTheme();

  if (!vehicle) {
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
        <div style={{ fontSize: "24px", opacity: 0.5 }}>🚗</div>
        <div style={{ fontSize: "13px" }}>Select a vehicle to view details</div>
      </div>
    );
  }

  const getStateConfig = (state: VehicleState) => {
    switch (state) {
      case "NORMAL":
        return { color: theme.colors.success, bg: theme.colors.successMuted, label: "Nominal" };
      case "ALERTING":
        return { color: theme.colors.warning, bg: theme.colors.warningMuted, label: "Alerting" };
      case "UNDER_INTERVENTION":
        return { color: theme.colors.critical, bg: theme.colors.criticalMuted, label: "Under Intervention" };
      default:
        return { color: theme.colors.textMuted, bg: theme.colors.surfaceSecondary, label: "Unknown" };
    }
  };

  const stateConfig = getStateConfig(vehicle.state);
  const isEgo = vehicle.vehicle_type === "Autonomous Vehicle" || vehicle.vehicle_id.includes("ego");

  // Format speed for display (m/s to km/h)
  const speedKmh = vehicle.last_speed != null ? (vehicle.last_speed * 3.6).toFixed(1) : null;
  
  // Format heading (radians to degrees)
  const headingDeg = vehicle.last_yaw != null 
    ? ((vehicle.last_yaw * 180 / Math.PI + 360) % 360).toFixed(0)
    : null;

  const InfoRow = ({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) => (
    <div style={{ marginBottom: "12px" }}>
      <div
        style={{ 
          fontSize: "10px", 
          color: theme.colors.textMuted, 
          marginBottom: "4px",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div 
        style={{ 
          fontSize: "13px", 
          color: theme.colors.text,
          fontFamily: mono ? theme.fonts.mono : "inherit",
        }}
      >
        {value}
      </div>
    </div>
  );

  return (
    <div style={{ padding: "16px" }}>
      {/* Header */}
      <div style={{ 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "space-between",
        marginBottom: "16px",
      }}>
        <h2 style={{ 
          margin: 0, 
          fontSize: "14px", 
          fontWeight: 700, 
          color: theme.colors.textSecondary,
          letterSpacing: "0.5px",
        }}>
          VEHICLE
        </h2>
        {isEgo && (
          <span
            style={{
              fontSize: "10px",
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: "4px",
              backgroundColor: theme.colors.primaryMuted,
              color: theme.colors.primary,
            }}
          >
            AV
          </span>
        )}
      </div>

      {/* Vehicle ID */}
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
          {vehicle.vehicle_display_id || vehicle.vehicle_id}
        </div>
        {vehicle.vehicle_display_id && (
          <div
            style={{
              fontSize: "11px",
              color: theme.colors.textMuted,
              fontFamily: theme.fonts.mono,
            }}
          >
            {vehicle.vehicle_id}
          </div>
        )}
      </div>

      {/* State Badge */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "6px 12px",
            borderRadius: "6px",
            backgroundColor: stateConfig.bg,
          }}
        >
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: stateConfig.color,
              animation: vehicle.state !== "NORMAL" ? "pulse 2s infinite" : undefined,
            }}
          />
          <span
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: stateConfig.color,
            }}
          >
            {stateConfig.label}
          </span>
        </div>
      </div>

      {/* Vehicle Info Grid */}
      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "1fr 1fr",
        gap: "8px",
        padding: "12px",
        backgroundColor: theme.colors.surfaceSecondary,
        borderRadius: "8px",
        marginBottom: "12px",
      }}>
        <InfoRow label="Type" value={vehicle.vehicle_type || (isEgo ? "Autonomous" : "Tracked")} />
        <InfoRow label="Open Alerts" value={
          <span style={{ 
            color: vehicle.open_alerts_count > 0 ? theme.colors.warning : theme.colors.success,
            fontWeight: 600,
          }}>
            {vehicle.open_alerts_count}
          </span>
        } />
        
        {speedKmh && (
          <InfoRow 
            label="Speed" 
            value={`${speedKmh} km/h`}
            mono
          />
        )}
        
        {headingDeg && (
          <InfoRow 
            label="Heading" 
            value={`${headingDeg}°`}
            mono
          />
        )}
      </div>

      {/* Position */}
      {vehicle.last_position_x !== null && vehicle.last_position_y !== null && (
        <div style={{ 
          padding: "12px",
          backgroundColor: theme.colors.surfaceSecondary,
          borderRadius: "8px",
          marginBottom: "12px",
        }}>
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
            Position
          </div>
          <div style={{ 
            display: "grid", 
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
            fontFamily: theme.fonts.mono,
            fontSize: "12px",
            color: theme.colors.text,
          }}>
            <div>X: {vehicle.last_position_x.toFixed(2)} m</div>
            <div>Y: {vehicle.last_position_y.toFixed(2)} m</div>
          </div>
        </div>
      )}

      {/* Assigned Operator */}
      {vehicle.assigned_operator && (
        <InfoRow 
          label="Assigned Operator" 
          value={vehicle.assigned_operator}
        />
      )}

      {/* Last Updated */}
      <div style={{ 
        fontSize: "10px", 
        color: theme.colors.textMuted,
        borderTop: `1px solid ${theme.colors.border}`,
        paddingTop: "12px",
        marginTop: "8px",
      }}>
        Last updated: {new Date(vehicle.updated_at).toLocaleTimeString()}
      </div>

      {/* CSS for animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
