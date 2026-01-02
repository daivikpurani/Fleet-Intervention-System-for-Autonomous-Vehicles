// Operator action buttons component

import { useState } from "react";
import { api } from "../services/api";
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
  const [operatorId, setOperatorId] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAction = async (
    actionFn: () => Promise<any>,
    actionName: string
  ) => {
    try {
      setLoading(actionName);
      setError(null);
      await actionFn();
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
      "acknowledge"
    );
  };

  const handleResolve = () => {
    if (!alert) return;
    handleAction(
      () => api.resolveAlert(alert.id),
      "resolve"
    );
  };

  const handleVehicleAction = (actionType: ActionType) => {
    if (!vehicle) return;
    handleAction(
      () => api.createVehicleAction(vehicle.vehicle_id, actionType),
      actionType
    );
  };

  const handleAssignOperator = () => {
    if (!vehicle || !operatorId.trim()) return;
    handleAction(
      () => api.assignOperator(vehicle.vehicle_id, operatorId.trim()),
      "assign"
    );
    setOperatorId("");
  };

  const buttonStyle: React.CSSProperties = {
    padding: "8px 16px",
    margin: "4px",
    border: "1px solid #ddd",
    borderRadius: "4px",
    backgroundColor: "#fff",
    cursor: "pointer",
    fontSize: "12px",
    transition: "all 0.2s",
  };

  const disabledStyle: React.CSSProperties = {
    ...buttonStyle,
    opacity: 0.5,
    cursor: "not-allowed",
  };

  return (
    <div style={{ padding: "16px" }}>
      <h2 style={{ margin: "0 0 16px 0", fontSize: "18px" }}>Actions</h2>

      {error && (
        <div
          style={{
            padding: "8px",
            marginBottom: "12px",
            backgroundColor: "#ffebee",
            color: "#c62828",
            borderRadius: "4px",
            fontSize: "12px",
          }}
        >
          {error}
        </div>
      )}

      {/* Alert Actions */}
      {alert && (
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
            Alert Actions
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <button
              onClick={handleAcknowledge}
              disabled={alert.status !== "OPEN" || loading !== null}
              style={alert.status === "OPEN" && !loading ? buttonStyle : disabledStyle}
            >
              {loading === "acknowledge" ? "Acknowledging..." : "ACKNOWLEDGE"}
            </button>
            <button
              onClick={handleResolve}
              disabled={
                (alert.status !== "OPEN" && alert.status !== "ACKNOWLEDGED") ||
                loading !== null
              }
              style={
                (alert.status === "OPEN" || alert.status === "ACKNOWLEDGED") && !loading
                  ? buttonStyle
                  : disabledStyle
              }
            >
              {loading === "resolve" ? "Resolving..." : "RESOLVE"}
            </button>
          </div>
        </div>
      )}

      {/* Vehicle Actions */}
      {vehicle && (
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
            Vehicle Actions
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <button
              onClick={() => handleVehicleAction("PULL_OVER_SIMULATED")}
              disabled={loading !== null}
              style={!loading ? buttonStyle : disabledStyle}
            >
              {loading === "PULL_OVER_SIMULATED"
                ? "Processing..."
                : "PULL_OVER_SIMULATED"}
            </button>
            <button
              onClick={() => handleVehicleAction("REQUEST_REMOTE_ASSIST")}
              disabled={loading !== null}
              style={!loading ? buttonStyle : disabledStyle}
            >
              {loading === "REQUEST_REMOTE_ASSIST"
                ? "Processing..."
                : "REQUEST_REMOTE_ASSIST"}
            </button>
            <button
              onClick={() => handleVehicleAction("RESUME_SIMULATION")}
              disabled={loading !== null}
              style={!loading ? buttonStyle : disabledStyle}
            >
              {loading === "RESUME_SIMULATION"
                ? "Processing..."
                : "RESUME_SIMULATION"}
            </button>
          </div>
        </div>
      )}

      {/* Assign Operator */}
      {vehicle && (
        <div>
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
            Assign Operator
          </div>
          <div style={{ display: "flex", gap: "4px" }}>
            <input
              type="text"
              value={operatorId}
              onChange={(e) => setOperatorId(e.target.value)}
              placeholder="Operator ID"
              style={{
                flex: 1,
                padding: "4px 8px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                fontSize: "12px",
              }}
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  handleAssignOperator();
                }
              }}
            />
            <button
              onClick={handleAssignOperator}
              disabled={!operatorId.trim() || loading !== null}
              style={
                operatorId.trim() && !loading ? buttonStyle : disabledStyle
              }
            >
              {loading === "assign" ? "Assigning..." : "ASSIGN"}
            </button>
          </div>
        </div>
      )}

      {!alert && !vehicle && (
        <div style={{ fontSize: "12px", color: "#888", textAlign: "center" }}>
          Select an alert or vehicle to perform actions
        </div>
      )}
    </div>
  );
}
