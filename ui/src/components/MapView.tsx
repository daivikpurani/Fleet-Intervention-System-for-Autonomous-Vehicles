// MapboxGL map component with enhanced vehicle visualization

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useTheme } from "../contexts/ThemeContext";
import type { Vehicle, VehicleState } from "../types";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || "";

// Coordinate transformation constants
// This is a visualization mapping, not real geography
const COORD_SCALE = 1e-5; // Scale factor for x,y to lng,lat conversion

interface MapViewProps {
  vehicles: Vehicle[];
  selectedVehicleId: string | null;
  onVehicleClick: (vehicleId: string) => void;
  mapCenter?: { x: number; y: number } | null;
}

export function MapView({
  vehicles,
  selectedVehicleId,
  onVehicleClick,
  mapCenter,
}: MapViewProps) {
  const { theme } = useTheme();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<Map<string, mapboxgl.Marker>>(new Map());
  const [initialCenter, setInitialCenter] = useState<{
    lng: number;
    lat: number;
  } | null>(null);

  // Initialize map center from first ego vehicle or provided center
  useEffect(() => {
    if (initialCenter) return;

    const egoVehicle = vehicles.find(
      (v) => v.vehicle_type === "Autonomous Vehicle" || v.vehicle_id.includes("ego")
    );
    const centerVehicle = egoVehicle || vehicles[0];

    if (centerVehicle != null && centerVehicle.last_position_x != null && centerVehicle.last_position_y != null) {
      const lng0 = -122.4194; // San Francisco as base (arbitrary, just for visualization)
      const lat0 = 37.7749;
      const lng = lng0 + centerVehicle.last_position_x * COORD_SCALE;
      const lat = lat0 + centerVehicle.last_position_y * COORD_SCALE;

      setInitialCenter({ lng, lat });
    } else if (mapCenter) {
      const lng0 = -122.4194;
      const lat0 = 37.7749;
      const lng = lng0 + mapCenter.x * COORD_SCALE;
      const lat = lat0 + mapCenter.y * COORD_SCALE;
      setInitialCenter({ lng, lat });
    }
  }, [vehicles, mapCenter, initialCenter]);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || !MAPBOX_TOKEN || initialCenter === null) return;

    // Use dark style in dark mode, light style in light mode
    const mapStyle =
      theme.mode === "dark"
        ? "mapbox://styles/mapbox/dark-v11"
        : "mapbox://styles/mapbox/streets-v12";

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: mapStyle,
      center: [initialCenter.lng, initialCenter.lat],
      zoom: 15,
      accessToken: MAPBOX_TOKEN,
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [initialCenter, theme.mode]);

  // Update vehicle markers
  useEffect(() => {
    if (!mapRef.current || initialCenter === null) return;

    const map = mapRef.current;
    const lng0 = -122.4194;
    const lat0 = 37.7749;

    // Remove markers for vehicles that no longer exist
    const currentVehicleIds = new Set(vehicles.map((v) => v.vehicle_id));
    for (const [vehicleId, marker] of markersRef.current.entries()) {
      if (!currentVehicleIds.has(vehicleId)) {
        marker.remove();
        markersRef.current.delete(vehicleId);
      }
    }

    // Update or create markers
    vehicles.forEach((vehicle) => {
      if (
        vehicle.last_position_x === null ||
        vehicle.last_position_y === null
      ) {
        return;
      }

      const lng = lng0 + vehicle.last_position_x * COORD_SCALE;
      const lat = lat0 + vehicle.last_position_y * COORD_SCALE;

      // Get color based on state
      const getStateColor = (state: VehicleState): string => {
        switch (state) {
          case "NORMAL":
            return theme.colors.success;
          case "ALERTING":
            return theme.colors.warning;
          case "UNDER_INTERVENTION":
            return theme.colors.critical;
          default:
            return theme.colors.textMuted;
        }
      };

      const isEgo = vehicle.vehicle_type === "Autonomous Vehicle" || vehicle.vehicle_id.includes("ego");
      const isSelected = vehicle.vehicle_id === selectedVehicleId;
      const baseSize = isEgo ? 16 : 10;
      const size = isSelected ? baseSize + 4 : baseSize;
      const color = getStateColor(vehicle.state);
      
      // Convert yaw (radians) to degrees for rotation
      // Yaw is typically counter-clockwise from east, we need clockwise from north
      const rotationDeg = vehicle.last_yaw != null 
        ? (90 - (vehicle.last_yaw * 180 / Math.PI)) % 360 
        : 0;

      const existingMarker = markersRef.current.get(vehicle.vehicle_id);

      if (existingMarker) {
        // Update existing marker position
        existingMarker.setLngLat([lng, lat]);
        // Update marker element style
        const el = existingMarker.getElement();
        if (el) {
          updateMarkerElement(el, vehicle, isEgo, isSelected, size, color, rotationDeg);
        }
      } else {
        // Create new marker
        const el = createMarkerElement(vehicle, isEgo, isSelected, size, color, rotationDeg);

        const marker = new mapboxgl.Marker({ element: el })
          .setLngLat([lng, lat])
          .addTo(map);

        el.addEventListener("click", () => {
          onVehicleClick(vehicle.vehicle_id);
        });

        markersRef.current.set(vehicle.vehicle_id, marker);
      }
    });
  }, [vehicles, selectedVehicleId, onVehicleClick, initialCenter, theme]);

  // Helper to create marker element
  const createMarkerElement = (
    vehicle: Vehicle,
    isEgo: boolean,
    isSelected: boolean,
    size: number,
    color: string,
    rotationDeg: number
  ): HTMLDivElement => {
    const el = document.createElement("div");
    el.className = "vehicle-marker";
    updateMarkerElement(el, vehicle, isEgo, isSelected, size, color, rotationDeg);
    return el;
  };

  // Helper to update marker element styles
  const updateMarkerElement = (
    el: HTMLElement,
    vehicle: Vehicle,
    isEgo: boolean,
    isSelected: boolean,
    size: number,
    color: string,
    rotationDeg: number
  ) => {
    const showHeading = vehicle.last_yaw != null;
    
    if (isEgo) {
      // Ego vehicle: triangle/arrow shape with heading
      el.style.width = `${size}px`;
      el.style.height = `${size}px`;
      el.style.borderRadius = "0";
      el.style.backgroundColor = "transparent";
      el.style.border = "none";
      el.style.cursor = "pointer";
      el.style.transform = showHeading ? `rotate(${rotationDeg}deg)` : "";
      el.style.transition = "transform 0.3s ease-out";
      
      // Create triangle using borders (pointing up by default)
      el.style.borderLeft = `${size / 2}px solid transparent`;
      el.style.borderRight = `${size / 2}px solid transparent`;
      el.style.borderBottom = `${size}px solid ${color}`;
      
      if (isSelected) {
        el.style.filter = `drop-shadow(0 0 4px ${color}) drop-shadow(0 0 8px ${color})`;
      } else {
        el.style.filter = `drop-shadow(0 2px 3px rgba(0,0,0,0.3))`;
      }
    } else {
      // Tracked vehicle: circle with optional direction indicator
      el.style.width = `${size}px`;
      el.style.height = `${size}px`;
      el.style.borderRadius = "50%";
      el.style.backgroundColor = color;
      el.style.border = isSelected 
        ? `2px solid ${theme.mode === "dark" ? "#fff" : "#000"}`
        : `1px solid ${color}`;
      el.style.cursor = "pointer";
      el.style.boxShadow = isSelected 
        ? `0 0 8px ${color}, 0 0 16px ${color}`
        : theme.mode === "dark" 
          ? "0 2px 4px rgba(0,0,0,0.5)"
          : "0 2px 4px rgba(0,0,0,0.3)";
      
      // Reset triangle styles if previously used
      el.style.borderLeft = "";
      el.style.borderRight = "";
      el.style.borderBottom = "";
      el.style.transform = "";
      el.style.filter = "";
    }
  };

  if (!MAPBOX_TOKEN) {
    return (
      <div 
        style={{ 
          padding: "40px", 
          textAlign: "center", 
          color: theme.colors.textSecondary,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          backgroundColor: theme.colors.background,
        }}
      >
        <div style={{ fontSize: "32px", marginBottom: "16px" }}>🗺️</div>
        <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>
          Map Not Configured
        </div>
        <div style={{ fontSize: "12px", color: theme.colors.textMuted, maxWidth: "300px" }}>
          Set <code style={{ 
            backgroundColor: theme.colors.surfaceSecondary, 
            padding: "2px 6px", 
            borderRadius: "4px",
            fontFamily: theme.fonts.mono,
          }}>VITE_MAPBOX_TOKEN</code> environment variable to enable the map view.
        </div>
      </div>
    );
  }

  if (initialCenter === null) {
    return (
      <div 
        style={{ 
          padding: "40px", 
          textAlign: "center", 
          color: theme.colors.textMuted,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            border: `3px solid ${theme.colors.border}`,
            borderTopColor: theme.colors.primary,
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            marginBottom: "16px",
          }}
        />
        <div style={{ fontSize: "13px" }}>Waiting for vehicle telemetry...</div>
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div
      ref={mapContainerRef}
      style={{ width: "100%", height: "100%", minHeight: "400px" }}
    />
  );
}
