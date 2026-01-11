/**
 * Synthetic route definitions for realistic vehicle visualization on San Francisco map.
 * 
 * Maps L5Kit vehicle coordinates (x, y in meters) to actual SF road lat/lng positions.
 * Zero API calls, deterministic mapping for consistent demo visualization.
 */

export interface RouteWaypoint {
  lat: number;
  lng: number;
}

export interface RouteDefinition {
  id: string;
  name: string;
  waypoints: RouteWaypoint[];
  totalLength: number; // Cached total length in degrees for interpolation
}

export interface MappedPosition {
  lng: number;
  lat: number;
  bearing: number; // Direction in degrees (0 = north, 90 = east)
}

// Pre-defined SF road routes with actual lat/lng waypoints
// Each route follows real road geometry for realistic visualization
const SF_ROUTES: RouteDefinition[] = [
  {
    id: 'market-street',
    name: 'Market Street',
    waypoints: [
      { lat: 37.7955, lng: -122.3937 }, // Embarcadero & Market
      { lat: 37.7902, lng: -122.4000 }, // Montgomery St
      { lat: 37.7867, lng: -122.4035 }, // Powell St
      { lat: 37.7835, lng: -122.4078 }, // Civic Center
      { lat: 37.7750, lng: -122.4183 }, // Van Ness
      { lat: 37.7686, lng: -122.4294 }, // Church St
      { lat: 37.7615, lng: -122.4350 }, // Castro
    ],
    totalLength: 0,
  },
  {
    id: 'mission-street',
    name: 'Mission Street',
    waypoints: [
      { lat: 37.7909, lng: -122.3960 }, // Embarcadero & Mission
      { lat: 37.7880, lng: -122.4020 }, // 1st & Mission
      { lat: 37.7850, lng: -122.4070 }, // 3rd & Mission
      { lat: 37.7820, lng: -122.4120 }, // 5th & Mission
      { lat: 37.7780, lng: -122.4180 }, // 7th & Mission
      { lat: 37.7650, lng: -122.4190 }, // 16th & Mission
      { lat: 37.7520, lng: -122.4185 }, // 24th & Mission
    ],
    totalLength: 0,
  },
  {
    id: 'van-ness',
    name: 'Van Ness Avenue',
    waypoints: [
      { lat: 37.8070, lng: -122.4231 }, // Bay & Van Ness
      { lat: 37.7990, lng: -122.4220 }, // Lombard & Van Ness
      { lat: 37.7920, lng: -122.4210 }, // Broadway & Van Ness
      { lat: 37.7850, lng: -122.4200 }, // California & Van Ness
      { lat: 37.7790, lng: -122.4190 }, // Geary & Van Ness
      { lat: 37.7750, lng: -122.4183 }, // Market & Van Ness
    ],
    totalLength: 0,
  },
  {
    id: 'geary-blvd',
    name: 'Geary Boulevard',
    waypoints: [
      { lat: 37.7870, lng: -122.4051 }, // Union Square
      { lat: 37.7854, lng: -122.4120 }, // Larkin & Geary
      { lat: 37.7815, lng: -122.4220 }, // Van Ness & Geary
      { lat: 37.7795, lng: -122.4350 }, // Fillmore & Geary
      { lat: 37.7792, lng: -122.4500 }, // Divisadero & Geary
      { lat: 37.7785, lng: -122.4650 }, // Masonic & Geary
      { lat: 37.7780, lng: -122.4800 }, // Park Presidio & Geary
    ],
    totalLength: 0,
  },
  {
    id: 'embarcadero',
    name: 'Embarcadero',
    waypoints: [
      { lat: 37.8075, lng: -122.4174 }, // Fisherman's Wharf
      { lat: 37.8050, lng: -122.4080 }, // Pier 39
      { lat: 37.8010, lng: -122.3975 }, // Pier 33
      { lat: 37.7970, lng: -122.3930 }, // Ferry Building
      { lat: 37.7920, lng: -122.3905 }, // Rincon Park
      { lat: 37.7870, lng: -122.3870 }, // South Beach
      { lat: 37.7785, lng: -122.3890 }, // AT&T Park area
    ],
    totalLength: 0,
  },
];

/**
 * Calculate distance between two waypoints (in degrees, for interpolation)
 */
function waypointDistance(a: RouteWaypoint, b: RouteWaypoint): number {
  const dlat = b.lat - a.lat;
  const dlng = b.lng - a.lng;
  return Math.sqrt(dlat * dlat + dlng * dlng);
}

/**
 * Calculate bearing between two waypoints (0-360 degrees, 0 = north)
 */
function calculateBearing(from: RouteWaypoint, to: RouteWaypoint): number {
  const dlng = to.lng - from.lng;
  const dlat = to.lat - from.lat;
  // atan2 returns angle from positive X axis, we want from north (positive Y)
  const angle = Math.atan2(dlng, dlat) * (180 / Math.PI);
  return (angle + 360) % 360;
}

// Initialize total lengths for each route
SF_ROUTES.forEach(route => {
  let total = 0;
  for (let i = 0; i < route.waypoints.length - 1; i++) {
    total += waypointDistance(route.waypoints[i], route.waypoints[i + 1]);
  }
  route.totalLength = total;
});

/**
 * Better hash function for even distribution across routes
 * Uses FNV-1a hash which has better distribution properties
 */
function hashString(str: string): number {
  let hash = 2166136261; // FNV offset basis
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash = Math.imul(hash, 16777619); // FNV prime
  }
  return Math.abs(hash >>> 0);
}

/**
 * Extract numeric part from vehicle ID for better distribution
 * Vehicle IDs like "0_track_328" -> use track number for routing
 */
function extractTrackNumber(vehicleId: string): number {
  // Try to extract track number from IDs like "0_track_328"
  const trackMatch = vehicleId.match(/track_(\d+)/);
  if (trackMatch) {
    return parseInt(trackMatch[1], 10);
  }
  // Try to extract any number from the ID
  const numMatch = vehicleId.match(/(\d+)/);
  if (numMatch) {
    return parseInt(numMatch[1], 10);
  }
  return hashString(vehicleId);
}

/**
 * Assign a vehicle to a route based on its ID (deterministic)
 * Uses track number for better distribution across routes
 */
export function assignVehicleToRoute(vehicleId: string): RouteDefinition {
  const trackNum = extractTrackNumber(vehicleId);
  // Use modulo with larger prime multiplier for better distribution across routes
  // This spreads vehicles more evenly across all available routes
  const routeIndex = (trackNum * 17 + 11) % SF_ROUTES.length;
  return SF_ROUTES[routeIndex];
}

/**
 * Map L5Kit coordinates to a position on the assigned route
 * 
 * @param x - L5Kit x coordinate (meters), used for slight lateral offset
 * @param y - L5Kit y coordinate (meters), used as progress along route
 * @param route - The assigned route definition
 * @returns Mapped position with lng, lat, and bearing
 */
export function mapPositionToRoute(
  x: number,
  y: number,
  route: RouteDefinition
): MappedPosition {
  // Normalize Y to progress along route (0 to 1)
  // Use modulo-based wrapping for cyclic distribution along route
  // This ensures vehicles are spread along the entire route regardless of Y range
  const cycleLength = 2000; // meters - increased to space vehicles further apart
  const normalizedProgress = ((y % cycleLength) + cycleLength) % cycleLength / cycleLength;
  
  // Add X-based offset to further spread vehicles
  const xOffset = ((x % 500) + 500) % 500 / 500 * 0.6; // Increased to 60% for better spacing
  const finalProgress = (normalizedProgress + xOffset) % 1.0;
  
  // Find position along route at this progress
  const targetDistance = finalProgress * route.totalLength;
  
  let accumulatedDistance = 0;
  let segmentIndex = 0;
  
  // Find which segment we're in
  for (let i = 0; i < route.waypoints.length - 1; i++) {
    const segmentLength = waypointDistance(route.waypoints[i], route.waypoints[i + 1]);
    if (accumulatedDistance + segmentLength >= targetDistance) {
      segmentIndex = i;
      break;
    }
    accumulatedDistance += segmentLength;
    segmentIndex = i;
  }
  
  // Ensure we don't go past the last segment
  if (segmentIndex >= route.waypoints.length - 1) {
    segmentIndex = route.waypoints.length - 2;
  }
  
  const segmentStart = route.waypoints[segmentIndex];
  const segmentEnd = route.waypoints[segmentIndex + 1];
  const segmentLength = waypointDistance(segmentStart, segmentEnd);
  
  // Progress within this segment
  const remainingDistance = targetDistance - accumulatedDistance;
  const segmentProgress = segmentLength > 0 ? Math.min(1, remainingDistance / segmentLength) : 0;
  
  // Interpolate position within segment
  let lat = segmentStart.lat + (segmentEnd.lat - segmentStart.lat) * segmentProgress;
  let lng = segmentStart.lng + (segmentEnd.lng - segmentStart.lng) * segmentProgress;
  
  // Apply small lateral offset based on X coordinate (lane simulation)
  // Convert X meters to approximate degrees (~111,000 meters per degree)
  const laneOffset = ((x % 15) - 7.5) / 111000; // ±7.5m offset for lane positioning
  const bearing = calculateBearing(segmentStart, segmentEnd);
  
  // Apply perpendicular offset (rotate 90 degrees from bearing)
  const perpAngle = (bearing + 90) * (Math.PI / 180);
  lng += laneOffset * Math.sin(perpAngle) * 0.8;
  lat += laneOffset * Math.cos(perpAngle) * 0.8;
  
  return { lng, lat, bearing };
}

/**
 * Get all available routes (for debugging/visualization)
 */
export function getAllRoutes(): RouteDefinition[] {
  return SF_ROUTES;
}

/**
 * Get the center point of all routes (for initial map centering)
 */
export function getRoutesCenter(): RouteWaypoint {
  // Return approximate center of SF routes
  return { lat: 37.7850, lng: -122.4100 };
}

