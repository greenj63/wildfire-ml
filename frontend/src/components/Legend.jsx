import { MIN_FIRE_ACRES, SIZE_BUCKETS } from "../fireSize";
import FlameIcon from "./FlameIcon";

export default function Legend({ count, error }) {
  return (
    <div className="legend">
      <div className="legend-title">
        Active wildfires of {MIN_FIRE_ACRES}+ acres
        {count !== null && <span className="legend-count"> ({count.toLocaleString("en-US")})</span>}
        <span className="legend-note"> · symbol size shows reported acres</span>
      </div>
      {error && <div className="legend-error">{error}</div>}
      <ul className="legend-items">
        {SIZE_BUCKETS.map((bucket) => (
          <li key={bucket.label}>
            <span className="legend-symbol">
              <FlameIcon size={bucket.px} />
            </span>
            {bucket.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
