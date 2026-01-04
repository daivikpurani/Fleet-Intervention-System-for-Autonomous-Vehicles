// Operator action buttons component with enhanced styling

import { useState } from "react";
import { api } from "../services/api";
import { useTheme } from "../contexts/ThemeContext";
import type { Alert, Vehicle, ActionType } from "../types";

interface ActionButtonsProps {
  alert: Alert | null;
  vehicle: Vehicle | null;
  onActionComplete?: () => void;
}

export function ActionButtons({
  alert,
  vehicle,
  onActionComplete,
}: ActionButtonsProps) {
  const { theme } = useTheme();
  const [operatorId, setOperatorId] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleAction = async (
    actionFn: () => Promise<any>,
    actionName: string,
    successMsg: string
  ) => {
    try {
      setLoading(actionName);
      setError(null);
      setSuccess(null);
      await actionFn();
      setSuccess(successMsg);
      setTimeout(() => setSuccess(null), 3000);
      if (onActionComplete) {
        onActionComplete();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setLoading(null);
    }
  };

  const handleAcknowledge = () => {
    if (!alert) return;
    handleAction(
      () => api.acknowledgeAlert(alert.id),
      "acknowledge",
      `${alert.incident_id || "Incident"} acknowledged`
    );
  };

  const handleResolve = () => {
    if (!alert) return;
    handleAction(
      () => api.resolveAlert(alert.id),
      "resolve",
      `${alert.incident_id || "Incident"} resolved`
    );
  };

  const handleVehicleAction = (actionType: ActionType, label: string) => {
    if (!vehicle) return;
    handleAction(
      () => api.createVehicleAction(vehicle.vehicle_id, actionType),
      actionType,
      `${label} executed`
    );
  };

  const handleAssignOperator = () => {
    if (!vehicle || !operatorId.trim()) return;
    handleAction(
      () => api.assignOperator(vehicle.vehicle_id, operatorId.trim()),
      "assign",
      `Operator ${operatorId.trim()} assigned`
    );
    setOperatorId("");
  };

  const ActionButton = ({
    onClick,
    disabled,
    loading: isLoading,
    children,
    variant = "default",
  }: {
    onClick: () => void;
    disabled?: boolean;
    loading?: boolean;
    children: React.ReactNode;
    variant?: "default" | "primary" | "success" | "warning" | "danger";
  }) => {
    const getVariantStyles = () => {
      if (disabled) {
        return {
          bg: theme.colors.surfaceSecondary,
          border: theme.colors.border,
          color: theme.colors.textMuted,
        };
      }
      switch (variant) {
        case "primary":
          return {
            bg: theme.colors.primaryMuted,
            border: theme.colors.primary,
            color: theme.colors.primary,
          };
        case "success":
          return {
            bg: theme.colors.successMuted,
            border: theme.colors.success,
            color: theme.colors.success,
          };
        case "warning":
          return {
            bg: theme.colors.warningMuted,
            border: theme.colors.warning,
            color: theme.colors.warning,
          };
        case "danger":
          return {
            bg: theme.colors.errorMuted,
            border: theme.colors.error,
            color: theme.colors.error,
          };
        default:
          return {
            bg: theme.colors.surfaceSecondary,
            border: theme.colors.border,
            color: theme.colors.text,
          };
      }
    };

    const styles = getVariantStyles();

    return (
      <button
        onClick={onClick}
        disabled={disabled}
        style={{
          padding: "8px 14px",
          border: `1px solid ${styles.border}`,
          borderRadius: "6px",
          backgroundColor: styles.bg,
          color: styles.color,
          cursor: disabled ? "not-allowed" : "pointer",
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "0.5px",
          transition: "all 0.2s",
          opacity: disabled ? 0.6 : 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "6px",
        }}
      >
        {isLoading && (
          <span
            style={{
              width: "12px",
              height: "12px",
              border: `2px solid ${styles.color}`,
              borderTopColor: "transparent",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
            }}
          />
        )}
        {children}
      </button>
    );
  };

  return (
    <div style={{ padding: "16px" }}>
      <h2 
        style={{ 
          margin: "0 0 16px 0", 
          fontSize: "14px", 
          fontWeight: 700, 
          color: theme.colors.textSecondary,
          letterSpacing: "0.5px",
        }}
      >
        ACTIONS
      </h2>

      {/* Status Messages */}
      {error && (
        <div
          style={{
            padding: "10px 12px",
            marginBottom: "12px",
            backgroundColor: theme.colors.errorMuted,
            color: theme.colors.error,
            borderRadius: "6px",
            fontSize: "12px",
            fontWeight: 500,
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {success && (
        <div
          style={{
            padding: "10px 12px",
            marginBottom: "12px",
            backgroundColor: theme.colors.successMuted,
            color: theme.colors.success,
            borderRadius: "6px",
            fontSize: "12px",
            fontWeight: 500,
            animation: "fadeIn 0.3s ease-out",
          }}
        >
          ✓ {success}
        </div>
      )}

      {/* Alert Actions */}
      {alert && (
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
            Incident Response
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <ActionButton
              onClick={handleAcknowledge}
              disabled={alert.status !== "OPEN" || loading !== null}
              loading={loading === "acknowledge"}
              variant="warning"
            >
              ACKNOWLEDGE
            </ActionButton>
            <ActionButton
              onClick={handleResolve}
              disabled={
                (alert.status !== "OPEN" && alert.status !== "ACKNOWLEDGED") ||
                loading !== null
              }
              loading={loading === "resolve"}
              variant="success"
            >
              RESOLVE
            </ActionButton>
          </div>
        </div>
      )}

      {/* Vehicle Actions */}
      {vehicle && (
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
            Vehicle Commands
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <ActionButton
              onClick={() => handleVehicleAction("PULL_OVER_SIMULATED", "Pull Over")}
              disabled={loading !== null}
              loading={loading === "PULL_OVER_SIMULATED"}
              variant="danger"
            >
              PULL OVER
            </ActionButton>
            <ActionButton
              onClick={() => handleVehicleAction("REQUEST_REMOTE_ASSIST", "Remote Assist")}
              disabled={loading !== null}
              loading={loading === "REQUEST_REMOTE_ASSIST"}
              variant="primary"
            >
              REQUEST REMOTE ASSIST
            </ActionButton>
            <ActionButton
              onClick={() => handleVehicleAction("RESUME_SIMULATION", "Resume")}
              disabled={loading !== null}
              loading={loading === "RESUME_SIMULATION"}
              variant="success"
            >
              RESUME OPERATIONS
            </ActionButton>
          </div>
        </div>
      )}

      {/* Assign Operator */}
      {vehicle && (
        <div>
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
            Assign Operator
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <input
              type="text"
              value={operatorId}
              onChange={(e) => setOperatorId(e.target.value)}
              placeholder="Operator ID"
              style={{
                flex: 1,
                padding: "8px 12px",
                border: `1px solid ${theme.colors.border}`,
                borderRadius: "6px",
                fontSize: "12px",
                backgroundColor: theme.colors.surfaceSecondary,
                color: theme.colors.text,
              }}
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  handleAssignOperator();
                }
              }}
            />
            <ActionButton
              onClick={handleAssignOperator}
              disabled={!operatorId.trim() || loading !== null}
              loading={loading === "assign"}
            >
              ASSIGN
            </ActionButton>
          </div>
        </div>
      )}

      {!alert && !vehicle && (
        <div 
          style={{ 
            fontSize: "13px", 
            color: theme.colors.textMuted, 
            textAlign: "center",
            padding: "20px",
          }}
        >
          Select an alert or vehicle to perform actions
        </div>
      )}

      {/* CSS for animations */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-5px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
