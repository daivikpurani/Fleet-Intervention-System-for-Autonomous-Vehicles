// REST API client for operator service

import type { Alert, Vehicle, Action, AlertStatus, ActionType } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8003";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = `${API_BASE_URL}${url}`;
  console.log("[api] Fetching:", fullUrl, options);
  
  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    console.log("[api] Response status:", response.status, response.statusText);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[api] Error response:", errorText);
      throw new ApiError(response.status, `API error: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("[api] Response data:", data);
    return data;
  } catch (error) {
    console.error("[api] Fetch error:", error);
    throw error;
  }
}

export const api = {
  // Alerts
  async getAlerts(status?: AlertStatus, vehicleId?: string): Promise<Alert[]> {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    if (vehicleId) params.append("vehicle_id", vehicleId);
    const query = params.toString() ? `?${params.toString()}` : "";
    return fetchJson<Alert[]>(`/alerts${query}`);
  },

  async getAlert(id: string): Promise<Alert> {
    return fetchJson<Alert>(`/alerts/${id}`);
  },

  async acknowledgeAlert(id: string, actor: string = "operator_ui"): Promise<Alert> {
    return fetchJson<Alert>(`/alerts/${id}/ack`, {
      method: "POST",
      body: JSON.stringify({ actor }),
    });
  },

  async resolveAlert(id: string, actor: string = "operator_ui"): Promise<Alert> {
    return fetchJson<Alert>(`/alerts/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ actor, action_type: "RESOLVE_ALERT" }),
    });
  },

  // Vehicles
  async getVehicles(): Promise<Vehicle[]> {
    return fetchJson<Vehicle[]>("/vehicles");
  },

  async getVehicle(id: string): Promise<Vehicle> {
    return fetchJson<Vehicle>(`/vehicles/${id}`);
  },

  async assignOperator(
    vehicleId: string,
    operatorId: string,
    actor: string = "operator_ui"
  ): Promise<Vehicle> {
    return fetchJson<Vehicle>(`/vehicles/${vehicleId}/assign`, {
      method: "POST",
      body: JSON.stringify({ operator_id: operatorId, actor }),
    });
  },

  async createVehicleAction(
    vehicleId: string,
    actionType: ActionType,
    actor: string = "operator_ui",
    payload: Record<string, any> = {}
  ): Promise<Action> {
    return fetchJson<Action>(`/vehicles/${vehicleId}/action`, {
      method: "POST",
      body: JSON.stringify({
        action_type: actionType,
        actor,
        payload,
      }),
    });
  },

  // Actions
  async getActions(vehicleId?: string): Promise<Action[]> {
    const query = vehicleId ? `?vehicle_id=${vehicleId}` : "";
    return fetchJson<Action[]>(`/actions${query}`);
  },
};
