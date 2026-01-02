// MapboxGL map component with vehicle visualization

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { Vehicle, VehicleState } from "../types";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || "";

// Coordinate transformation constants
// This is a visualization mapping, not real geography
// We use a small scale to keep coordinates visually stable
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

    const egoVehicle = vehicles.find((v) => v.vehicle_id.includes("ego"));
    const centerVehicle = egoVehicle || vehicles[0];

    if (centerVehicle != null && centerVehicle.last_position_x != null && centerVehicle.last_position_y != null) {
      // Use first vehicle position as map center
      // Apply affine transform: lng = lng0 + x * scale, lat = lat0 + y * scale
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

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [initialCenter.lng, initialCenter.lat],
      zoom: 15,
      accessToken: MAPBOX_TOKEN,
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [initialCenter]);

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
      const getColor = (state: VehicleState): string => {
        switch (state) {
          case "NORMAL":
            return "#888";
          case "ALERTING":
            return "#ff6b35";
          case "UNDER_INTERVENTION":
            return "#d32f2f";
          default:
            return "#888";
        }
      };

      const isSelected = vehicle.vehicle_id === selectedVehicleId;
      const radius = isSelected ? 12 : 8;
      const color = getColor(vehicle.state);

      const existingMarker = markersRef.current.get(vehicle.vehicle_id);

      if (existingMarker) {
        // Update existing marker position
        existingMarker.setLngLat([lng, lat]);
        // Update marker element style
        const el = existingMarker.getElement();
        if (el) {
          el.style.width = `${radius * 2}px`;
          el.style.height = `${radius * 2}px`;
          el.style.backgroundColor = color;
          el.style.borderColor = isSelected ? "#000" : color;
          el.style.borderWidth = isSelected ? "2px" : "1px";
        }
      } else {
        // Create new marker
        const el = document.createElement("div");
        el.className = "vehicle-marker";
        el.style.width = `${radius * 2}px`;
        el.style.height = `${radius * 2}px`;
        el.style.borderRadius = "50%";
        el.style.backgroundColor = color;
        el.style.border = `2px solid ${isSelected ? "#000" : color}`;
        el.style.cursor = "pointer";
        el.style.boxShadow = "0 2px 4px rgba(0,0,0,0.3)";

        const marker = new mapboxgl.Marker(el)
          .setLngLat([lng, lat])
          .addTo(map);

        el.addEventListener("click", () => {
          onVehicleClick(vehicle.vehicle_id);
        });

        markersRef.current.set(vehicle.vehicle_id, marker);
      }
    });
  }, [vehicles, selectedVehicleId, onVehicleClick, initialCenter]);

  if (!MAPBOX_TOKEN) {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <p>Mapbox token not configured. Set VITE_MAPBOX_TOKEN environment variable.</p>
      </div>
    );
  }

  if (initialCenter === null) {
    return (
      <div style={{ padding: "20px", textAlign: "center" }}>
        <p>Loading map...</p>
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
