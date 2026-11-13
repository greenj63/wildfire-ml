// Helpers for the line and bar charts (kept free of React so they can be tested).

// Round tick values up to 1, 2, 2.5, 5 x 10^n, from 0 to just past `max`.
export function niceTicks(max, count = 4) {
  if (!(max > 0)) return [0, 1];
  const rough = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough);
  const ticks = [];
  for (let value = 0; value < max + step; value += step) {
    ticks.push(Number(value.toPrecision(12)));
    if (value >= max) break;
  }
  return ticks;
}

// Index of the point whose x is closest to `x`
export function nearestIndex(xs, x) {
  let best = 0;
  xs.forEach((value, i) => {
    if (Math.abs(value - x) < Math.abs(xs[best] - x)) best = i;
  });
  return best;
}

// "1,234" / "12.3k" / "1.2M" for axis labels
export function compactNumber(value) {
  const abs = Math.abs(value);
  if (abs >= 1e6) return `${+(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e4) return `${+(value / 1e3).toFixed(1)}k`;
  return value.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

// Points from the API ({ date, acres, rate }) for one of the two charts.
// Rate has no value on the first day, so that point is left out.
export function toPoints(series, key) {
  return series
    .filter((p) => p[key] !== null && p[key] !== undefined)
    .map((p) => ({ x: Date.parse(`${p.date}T00:00:00Z`), y: p[key] }));
}
