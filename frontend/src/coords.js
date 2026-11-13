// Mirrors LOWER_48 in backend/app/fires.py: the models and live data cover only these.
export const BOUNDS = { south: 24, north: 50, west: -125, east: -66 };

export const OUTSIDE_MESSAGE =
  "Coordinates must be inside the continental US (latitude 24 to 50, longitude -125 to -66).";
export const FORMAT_MESSAGE = "Enter coordinates like (38.94, -123.32).";

const PAIR = /^\(?\s*(-?\d+(?:\.\d+)?)\s*(?:,|\s)\s*(-?\d+(?:\.\d+)?)\s*\)?$/;

export function isInsideUS(lat, lon) {
  return (
    lat >= BOUNDS.south &&
    lat <= BOUNDS.north &&
    lon >= BOUNDS.west &&
    lon <= BOUNDS.east
  );
}

// "38.94, -123.32", "(38.94, -123.32)" and "38.94 -123.32" all work.
// Returns { lat, lon } or { error }.
export function parseCoordinates(text) {
  const match = PAIR.exec(text.trim());
  if (!match) return { error: FORMAT_MESSAGE };
  const lat = Number(match[1]);
  const lon = Number(match[2]);
  if (!isInsideUS(lat, lon)) return { error: OUTSIDE_MESSAGE };
  return { lat, lon };
}

export function formatCoordinates(lat, lon) {
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}
