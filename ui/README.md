# FleetOps Operator Dashboard UI

React + MapboxGL dashboard for visualizing live vehicle telemetry and incident workflow.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and set:
- `VITE_API_BASE_URL`: Backend API URL (default: `http://localhost:8003`)
- `VITE_WS_URL`: WebSocket URL (default: `ws://localhost:8003/ws`)
- `VITE_MAPBOX_TOKEN`: Your Mapbox access token (get from https://account.mapbox.com/access-tokens/)

## Running

Start the development server:
```bash
npm run dev
```

The UI will be available at `http://localhost:5173` (or the port shown in the terminal).

## Features

- **Live Vehicle Tracking**: Vehicles appear on the map and update positions in real-time via WebSocket
- **Alert Management**: View alerts with filtering by status, severity, and vehicle ID
- **Incident Details**: View alert evidence including features, thresholds, and action history
- **Operator Actions**: 
  - Acknowledge/Resolve alerts
  - Vehicle actions: Pull Over, Request Remote Assist, Resume Simulation
  - Assign operators to vehicles
- **Demo Mode**: Auto-selects ego vehicle and opens first CRITICAL alert

## Layout

- **Left Column**: Alert list with filters
- **Center**: MapboxGL map showing vehicles as colored circles
- **Right Column**: Vehicle details, incident panel, and action buttons

## Map Coordinate System

The map uses a visualization coordinate system, not real geography. Vehicle positions (x, y in meters) are transformed to map coordinates using an affine mapping:

- `lng = lng0 + x * 1e-5`
- `lat = lat0 + y * 1e-5`

Where `lng0` and `lat0` are base coordinates (San Francisco area) used for visualization purposes only.

## Vehicle States

- **NORMAL**: Gray (#888)
- **ALERTING**: Orange (#ff6b35)
- **UNDER_INTERVENTION**: Red (#d32f2f)

## Prerequisites

- Node.js 18+
- Backend services running (operator-service, replay-service, anomaly-service)
- Mapbox access token

