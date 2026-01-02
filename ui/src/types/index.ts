// TypeScript type definitions for FleetOps UI

export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
export type VehicleState = "NORMAL" | "ALERTING" | "UNDER_INTERVENTION";
export type Severity = "INFO" | "WARNING" | "CRITICAL";
export type ActionType =
  | "ACKNOWLEDGE_ALERT"
  | "RESOLVE_ALERT"
  | "ASSIGN_OPERATOR"
  | "PULL_OVER_SIMULATED"
  | "REQUEST_REMOTE_ASSIST"
  | "RESUME_SIMULATION";

export interface Alert {
  id: string;
  vehicle_id: string;
  scene_id: string;
  frame_index: number;
  anomaly_id: string;
  rule_name: string;
  severity: Severity;
  status: AlertStatus;
  anomaly_payload: {
    features?: Record<string, any>;
    thresholds?: Record<string, any>;
    [key: string]: any;
  };
  first_seen_event_time: string;
  last_seen_event_time: string;
  created_at: string;
  updated_at: string;
}

export interface Vehicle {
  vehicle_id: string;
  state: VehicleState;
  assigned_operator: string | null;
  last_position_x: number | null;
  last_position_y: number | null;
  updated_at: string;
  open_alerts_count: number;
}

export interface Action {
  id: string;
  vehicle_id: string;
  alert_id: string | null;
  action_type: ActionType;
  actor: string;
  payload: Record<string, any>;
  created_at: string;
}

export interface WebSocketMessage {
  type: "alert_created" | "alert_updated" | "vehicle_updated" | "operator_action_created";
  data: Alert | Vehicle | Action;
}
