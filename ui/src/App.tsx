// Main App component with three-column layout

import { useState, useEffect, useRef } from "react";
import { api } from "./services/api";
import { useWebSocket } from "./hooks/useWebSocket";
import { MapView } from "./components/MapView";
import { AlertList } from "./components/AlertList";
import { VehicleDetail } from "./components/VehicleDetail";
import { IncidentPanel } from "./components/IncidentPanel";
import { ActionButtons } from "./components/ActionButtons";
import type { Vehicle, Alert, WebSocketMessage } from "./types";

function App() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mapCenter, setMapCenter] = useState<{ x: number; y: number } | null>(null);

  // Track demo mode actions to prevent duplicate triggers
  const demoEgoSelectedRef = useRef(false);

  // WebSocket connection status
  const { isConnected } = useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      if (message.type === "vehicle_updated") {
        const updatedVehicle = message.data as Vehicle;
        setVehicles((prev) => {
          const index = prev.findIndex((v) => v.vehicle_id === updatedVehicle.vehicle_id);
          if (index >= 0) {
            const newVehicles = [...prev];
            newVehicles[index] = updatedVehicle;
            return newVehicles;
          } else {
            return [...prev, updatedVehicle];
          }
        });

        // Demo mode: auto-select ego vehicle
        if (
          demoMode &&
          !demoEgoSelectedRef.current &&
          updatedVehicle.vehicle_id.includes("ego")
        ) {
          setSelectedVehicleId(updatedVehicle.vehicle_id);
          demoEgoSelectedRef.current = true;
        }
      }
    },
  });

  // Fetch initial vehicles
  useEffect(() => {
    async function fetchVehicles() {
      try {
        setLoading(true);
        setError(null);
        const fetchedVehicles = await api.getVehicles();
        setVehicles(fetchedVehicles);

        // Set map center from first ego vehicle
        const egoVehicle = fetchedVehicles.find((v) => v.vehicle_id.includes("ego"));
        if (egoVehicle && egoVehicle.last_position_x != null && egoVehicle.last_position_y != null) {
          setMapCenter({
            x: egoVehicle.last_position_x,
            y: egoVehicle.last_position_y,
          });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch vehicles");
      } finally {
        setLoading(false);
      }
    }

    fetchVehicles();
  }, []);


  const handleAlertClick = (alert: Alert) => {
    setSelectedAlert(alert);
    // Find and select the vehicle for this alert
    const vehicle = vehicles.find((v) => v.vehicle_id === alert.vehicle_id);
    if (vehicle) {
      setSelectedVehicleId(vehicle.vehicle_id);
    }
  };

  const handleVehicleClick = (vehicleId: string) => {
    setSelectedVehicleId(vehicleId);
    // Find alerts for this vehicle and select the first one if any
    // This will be handled by AlertList component
  };

  const handleActionComplete = () => {
    // Refresh vehicles and alerts after action
    api.getVehicles().then(setVehicles).catch(console.error);
  };

  const selectedVehicle = vehicles.find((v) => v.vehicle_id === selectedVehicleId) || null;

  // Demo mode: check for CRITICAL alerts on alert list updates
  // This is handled by AlertList component via the alert click handler

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #ddd",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "#f5f5f5",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "20px", fontWeight: "bold" }}>
          FleetOps Operator Dashboard
        </h1>
        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontSize: "12px",
              color: isConnected ? "#4caf50" : "#d32f2f",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: isConnected ? "#4caf50" : "#d32f2f",
              }}
            />
            {isConnected ? "Connected" : "Disconnected"}
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px" }}>
            <input
              type="checkbox"
              checked={demoMode}
              onChange={(e) => setDemoMode(e.target.checked)}
            />
            Demo Mode
          </label>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left Column: Alert List */}
        <div
          style={{
            width: "300px",
            borderRight: "1px solid #ddd",
            display: "flex",
            flexDirection: "column",
            backgroundColor: "#fff",
          }}
        >
          <AlertList onAlertClick={handleAlertClick} demoMode={demoMode} />
        </div>

        {/* Center Column: Map */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {loading ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                fontSize: "16px",
                color: "#888",
              }}
            >
              Loading...
            </div>
          ) : error ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                fontSize: "16px",
                color: "#d32f2f",
                gap: "8px",
              }}
            >
              <div>Error: {error}</div>
              {!isConnected && (
                <div style={{ fontSize: "14px", color: "#ff6b35" }}>
                  WebSocket disconnected. Reconnecting...
                </div>
              )}
            </div>
          ) : !isConnected ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                fontSize: "16px",
                color: "#ff6b35",
                backgroundColor: "#fff3e0",
                padding: "16px",
              }}
            >
              WebSocket disconnected. Live updates paused. Reconnecting...
            </div>
          ) : (
            <MapView
              vehicles={vehicles}
              selectedVehicleId={selectedVehicleId}
              onVehicleClick={handleVehicleClick}
              mapCenter={mapCenter}
            />
          )}
        </div>

        {/* Right Column: Vehicle Detail, Incident Panel, Actions */}
        <div
          style={{
            width: "350px",
            borderLeft: "1px solid #ddd",
            display: "flex",
            flexDirection: "column",
            backgroundColor: "#fff",
            overflowY: "auto",
          }}
        >
          <VehicleDetail vehicle={selectedVehicle} />
          <div style={{ borderTop: "1px solid #ddd", marginTop: "16px" }}>
            <IncidentPanel alert={selectedAlert} />
          </div>
          <div style={{ borderTop: "1px solid #ddd", marginTop: "16px" }}>
            <ActionButtons
              alert={selectedAlert}
              vehicle={selectedVehicle}
              onActionComplete={handleActionComplete}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
