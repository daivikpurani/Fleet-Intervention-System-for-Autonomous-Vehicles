// Alerts state management hook

import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "../services/api";
import { useWebSocket } from "./useWebSocket";
import type { Alert, AlertStatus, Severity, WebSocketMessage } from "../types";

export interface AlertFilters {
  status?: AlertStatus;
  severity?: Severity;
  vehicleId?: string;
}

export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AlertFilters>({});
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  // Fetch initial alerts
  useEffect(() => {
    let cancelled = false;

    async function fetchAlerts() {
      try {
        setLoading(true);
        setError(null);
        console.log("[useAlerts] Fetching alerts with filters:", filters);
        const fetchedAlerts = await api.getAlerts(filters.status, filters.vehicleId);
        console.log("[useAlerts] Fetched alerts:", fetchedAlerts.length, fetchedAlerts);
        if (!cancelled) {
          setAlerts(fetchedAlerts);
        }
      } catch (err) {
        console.error("[useAlerts] Error fetching alerts:", err);
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to fetch alerts");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchAlerts();

    return () => {
      cancelled = true;
    };
  }, [filters.status, filters.vehicleId]);

  // Handle WebSocket messages
  useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      if (message.type === "alert_created") {
        setAlerts((prev) => [message.data as Alert, ...prev]);
      } else if (message.type === "alert_updated") {
        setAlerts((prev) =>
          prev.map((alert) => (alert.id === (message.data as Alert).id ? (message.data as Alert) : alert))
        );
      }
    },
  });

  // Filter alerts
  const filteredAlerts = useMemo(() => {
    let result = alerts;
    console.log("[useAlerts] Filtering alerts. Total:", alerts.length, "Filters:", filters);

    if (filters.severity) {
      result = result.filter((alert) => alert.severity === filters.severity);
      console.log("[useAlerts] After severity filter:", result.length);
    }

    if (filters.vehicleId) {
      const searchTerm = filters.vehicleId.toLowerCase();
      result = result.filter((alert) =>
        alert.vehicle_id.toLowerCase().includes(searchTerm)
      );
      console.log("[useAlerts] After vehicleId filter:", result.length);
    }

    // Sort by last_seen_event_time (newest first)
    result = [...result].sort(
      (a, b) =>
        new Date(b.last_seen_event_time).getTime() -
        new Date(a.last_seen_event_time).getTime()
    );

    console.log("[useAlerts] Final filtered alerts:", result.length);
    return result;
  }, [alerts, filters]);

  const selectedAlert = useMemo(
    () => filteredAlerts.find((alert) => alert.id === selectedAlertId) || null,
    [filteredAlerts, selectedAlertId]
  );

  const updateFilters = useCallback((newFilters: Partial<AlertFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const selectAlert = useCallback((alertId: string | null) => {
    setSelectedAlertId(alertId);
  }, []);

  return {
    alerts: filteredAlerts,
    selectedAlert,
    loading,
    error,
    filters,
    updateFilters,
    selectAlert,
  };
}
