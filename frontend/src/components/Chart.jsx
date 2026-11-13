import { useId, useState } from "react";

import { compactNumber, nearestIndex, niceTicks } from "../chartMath";

const dayFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const fullDayFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

// kind "line" draws a filled line (acres so far); "bars" draws one bar per day (rate).
// `compact` is the small preview: no axes, and it stretches to fill its box.
export default function Chart({ points, kind, color, unit, compact = false }) {
  const [hover, setHover] = useState(null);
  const gradientId = useId();

  const W = compact ? 200 : 720;
  const H = compact ? 64 : 360;
  const pad = compact
    ? { left: 2, right: 2, top: 4, bottom: 4 }
    : { left: 56, right: 16, top: 16, bottom: 34 };
  const innerW = W - pad.left - pad.right;
  const innerH = H - pad.top - pad.bottom;

  const xs = points.map((p) => p.x);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const span = maxX - minX || 1;
  const maxY = Math.max(...points.map((p) => p.y), 0);
  const yTicks = niceTicks(maxY);
  const topY = yTicks[yTicks.length - 1];

  // Bars need room on both sides of the first and last day
  const barPad = kind === "bars" ? (span / Math.max(points.length - 1, 1)) * 0.5 : 0;
  const x = (value) => pad.left + ((value - (minX - barPad)) / (span + 2 * barPad)) * innerW;
  const y = (value) => pad.top + innerH - (value / topY) * innerH;
  const barWidth = Math.max(Math.min((innerW / points.length) * 0.7, 28), 1.5);

  const linePath = points.map((p, i) => `${i ? "L" : "M"}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L${x(maxX).toFixed(1)},${y(0)} L${x(minX).toFixed(1)},${y(0)} Z`;

  const xTickCount = Math.min(5, points.length);
  const xTicks = Array.from({ length: xTickCount }, (_, i) => minX + (span * i) / Math.max(xTickCount - 1, 1));

  function onMove(event) {
    if (compact) return;
    const box = event.currentTarget.getBoundingClientRect();
    const svgX = ((event.clientX - box.left) / box.width) * W;
    const dataX = (svgX - pad.left) / innerW * (span + 2 * barPad) + (minX - barPad);
    setHover(nearestIndex(xs, dataX));
  }

  const active = hover === null ? null : points[hover];
  const readoutRight = active && x(active.x) > W * 0.6;

  return (
    <svg
      className={`chart ${compact ? "compact" : ""}`}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio={compact ? "none" : "xMidYMid meet"}
      onPointerMove={onMove}
      onPointerLeave={() => setHover(null)}
      role="img"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {!compact &&
        yTicks.map((tick) => (
          <g key={tick}>
            <line x1={pad.left} x2={W - pad.right} y1={y(tick)} y2={y(tick)} className="grid" />
            <text x={pad.left - 8} y={y(tick)} className="tick" textAnchor="end" dominantBaseline="middle">
              {compactNumber(tick)}
            </text>
          </g>
        ))}
      {!compact &&
        xTicks.map((tick) => (
          <text key={tick} x={x(tick)} y={H - 10} className="tick" textAnchor="middle">
            {dayFormat.format(tick)}
          </text>
        ))}
      {compact && <line x1={pad.left} x2={W - pad.right} y1={y(0)} y2={y(0)} className="grid" vectorEffect="non-scaling-stroke" />}

      {kind === "bars" ? (
        points.map((p, i) => (
          <rect
            key={p.x}
            x={x(p.x) - barWidth / 2}
            y={y(p.y)}
            width={barWidth}
            height={Math.max(y(0) - y(p.y), 0)}
            fill={color}
            opacity={hover === null || hover === i ? 0.9 : 0.45}
          />
        ))
      ) : (
        <>
          <path d={areaPath} fill={`url(#${gradientId})`} />
          <path d={linePath} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        </>
      )}

      {active && (
        <g pointerEvents="none">
          <line x1={x(active.x)} x2={x(active.x)} y1={pad.top} y2={y(0)} className="crosshair" />
          {kind === "line" && <circle cx={x(active.x)} cy={y(active.y)} r="5" fill="#fff" stroke={color} strokeWidth="2.5" />}
          <g transform={`translate(${readoutRight ? x(active.x) - 8 : x(active.x) + 8},${pad.top + 4})`}>
            <text className="readout" textAnchor={readoutRight ? "end" : "start"}>
              <tspan x="0" dy="1em" fontWeight="700">
                {fullDayFormat.format(active.x)}
              </tspan>
              <tspan x="0" dy="1.3em">
                {active.y.toLocaleString("en-US", { maximumFractionDigits: 1 })} {unit}
              </tspan>
            </text>
          </g>
        </g>
      )}
    </svg>
  );
}
