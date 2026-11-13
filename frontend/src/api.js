async function getJson(url, signal) {
  const response = await fetch(url, { signal });
  let body = null;
  try {
    body = await response.json();
  } catch {
    // not JSON (for example the backend is not running)
  }
  if (!response.ok) {
    throw new Error(
      body?.detail && typeof body.detail === "string"
        ? body.detail
        : "The prediction server did not respond. Is the backend running?",
    );
  }
  return body;
}

export function fetchFires(signal) {
  return getJson("/api/fires", signal);
}

export function fetchPrediction(lat, lon, signal) {
  return getJson(`/api/predict?lat=${lat}&lon=${lon}`, signal);
}

export function fetchFireHistory(irwinId, signal) {
  return getJson(`/api/fires/history?irwin_id=${encodeURIComponent(irwinId)}`, signal);
}
