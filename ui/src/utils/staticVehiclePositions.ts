/**
 * Static hard-coded vehicle positions for the map.
 * 30 positions spaced out across the San Francisco area.
 */

export interface StaticPosition {
  lat: number;
  lng: number;
  bearing: number; // Direction in degrees (0 = north, 90 = east)
}

// 30 static positions randomly scattered across San Francisco city area
// All positions are on land, avoiding water areas (bay to the east, ocean to the west)
// Randomly distributed to avoid grid/linear patterns
export const STATIC_VEHICLE_POSITIONS: StaticPosition[] = [
  // Randomly scattered positions across central SF
  { lat: 37.7912, lng: -122.4195, bearing: 42 },
  { lat: 37.7887, lng: -122.4158, bearing: 87 },
  { lat: 37.7853, lng: -122.4212, bearing: 153 },
  { lat: 37.7796, lng: -122.4134, bearing: 68 },
  { lat: 37.7874, lng: -122.4107, bearing: 124 },
  
  { lat: 37.7839, lng: -122.4176, bearing: 31 },
  { lat: 37.7768, lng: -122.4251, bearing: 196 },
  { lat: 37.7895, lng: -122.4228, bearing: 79 },
  { lat: 37.7817, lng: -122.4119, bearing: 142 },
  { lat: 37.7742, lng: -122.4183, bearing: 267 },
  
  { lat: 37.7861, lng: -122.4142, bearing: 95 },
  { lat: 37.7908, lng: -122.4126, bearing: 58 },
  { lat: 37.7783, lng: -122.4237, bearing: 173 },
  { lat: 37.7846, lng: -122.4191, bearing: 211 },
  { lat: 37.7775, lng: -122.4154, bearing: 289 },
  
  { lat: 37.7882, lng: -122.4245, bearing: 36 },
  { lat: 37.7824, lng: -122.4208, bearing: 118 },
  { lat: 37.7759, lng: -122.4121, bearing: 245 },
  { lat: 37.7898, lng: -122.4173, bearing: 72 },
  { lat: 37.7804, lng: -122.4216, bearing: 189 },
  
  { lat: 37.7876, lng: -122.4137, bearing: 104 },
  { lat: 37.7841, lng: -122.4169, bearing: 227 },
  { lat: 37.7789, lng: -122.4194, bearing: 51 },
  { lat: 37.7763, lng: -122.4148, bearing: 138 },
  { lat: 37.7905, lng: -122.4219, bearing: 283 },
  
  { lat: 37.7832, lng: -122.4123, bearing: 165 },
  { lat: 37.7791, lng: -122.4178, bearing: 94 },
  { lat: 37.7858, lng: -122.4254, bearing: 47 },
  { lat: 37.7778, lng: -122.4201, bearing: 212 },
  { lat: 37.7813, lng: -122.4156, bearing: 301 },
];

/**
 * Get a static position for a vehicle by index.
 * Uses modulo to cycle through positions if there are more vehicles than positions.
 */
export function getStaticPosition(vehicleIndex: number): StaticPosition {
  const index = vehicleIndex % STATIC_VEHICLE_POSITIONS.length;
  return STATIC_VEHICLE_POSITIONS[index];
}

/**
 * Get the center point of all static positions (for initial map centering)
 */
export function getStaticPositionsCenter(): { lat: number; lng: number } {
  // Center of the city core area
  return { lat: 37.7820, lng: -122.4140 };
}
