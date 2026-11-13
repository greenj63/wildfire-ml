import { useEffect, useState } from "react";

import { fetchFireHistory } from "../api";
import { toPoints } from "../chartMath";
import { formatAcres, formatDate, formatPercent, formatRate } from "../format";
import ExpandableChart from "./ExpandableChart";

// Loads the day-by-day history for a fire and shows the two charts when there is one.
function FireCharts({ irwinId }) {
  const [state, setState] = useState({ status: "loading", series: [] });

  useEffect(() => {
    if (!irwinId) {
      setState({ status: "empty", series: [] });
      return undefined;
    }
    const controller = new AbortController();
    setState({ status: "loading", series: [] });
    fetchFireHistory(irwinId, controller.signal)
      .then((data) =>
        setState({ status: data.series.length >= 2 ? "ready" : "empty", series: data.series }),
      )
      .catch((problem) => {
        if (problem.name !== "AbortError") setState({ status: "error", series: [] });
      });
    return () => controller.abort();
  }, [irwinId]);

  if (state.status === "loading") return <p className="muted chart-status">Loading fire history…</p>;
  if (state.status !== "ready") {
    return (
      <p className="muted chart-status">
        {state.status === "error" ? "Could not load the fire history." : "No day-by-day history is available for this fire."}
      </p>
    );
  }
  const rate = toPoints(state.series, "rate");
  return (
    <div className="charts">
      <ExpandableChart
        title="Acres over time"
        points={toPoints(state.series, "acres")}
        kind="line"
        color="#d6451a"
        unit="acres"
        note="Mapped fire perimeter size from NIFC daily perimeters. It can differ slightly from the reported size above."
      />
      {rate.length > 0 && (
        <ExpandableChart
          title="Spread rate over time"
          points={rate}
          kind="bars"
          color="#e08a00"
          unit="acres/day"
          note="Acres added per day between mapped perimeters (a day with no new map shows the average since the last one)."
        />
      )}
    </div>
  );
}

function ModelRow({ model }) {
  return (
    <li>
      <span>{model.label}</span>
      <span className={model.status === "ok" ? "" : "muted"}>
        {model.status === "ok"
          ? formatRate(model.spread_rate)
          : model.status === "not_trained"
            ? "Not trained yet"
            : "Unavailable"}
      </span>
    </li>
  );
}

function OtherModels({ models }) {
  const [open, setOpen] = useState(false);
  if (models.length === 0) return null;
  return (
    <div className="other-models">
      <button
        type="button"
        className="toggle"
        aria-expanded={open}
        aria-controls="other-models-list"
        onClick={() => setOpen(!open)}
      >
        Other models <span className={`chevron ${open ? "open" : ""}`}>▾</span>
      </button>
      <div id="other-models-list" className={`reveal ${open ? "open" : ""}`} aria-hidden={!open}>
        <ul className="model-list">
          {models.map((model) => (
            <ModelRow key={model.name} model={model} />
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function ResultPanel({ status, result, error }) {
  if (status === "idle") {
    return (
      <p className="placeholder">
        Click a point on the map or
        <br />
        enter coordinates to get started
      </p>
    );
  }
  if (status === "loading") {
    return (
      <div className="loading" role="status">
        <div className="spinner" />
        <p>Gathering live weather, drought and terrain data…</p>
        <p className="muted">This usually takes under a minute.</p>
      </div>
    );
  }
  if (status === "error") {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    );
  }

  const main = result.models.find((model) => model.name === result.primary_model);
  const others = result.models.filter((model) => model.name !== result.primary_model);
  const { latitude, longitude } = result.location;
  const fire = result.nearby_fire;

  return (
    <div className="result">
      <p className="result-location">
        {latitude.toFixed(4)}, {longitude.toFixed(4)}
      </p>

      <section>
        <h2>Predicted spread rate</h2>
        <p className="big-number">{main?.status === "ok" ? formatRate(main.spread_rate) : "Unavailable"}</p>
        <p className="muted">{main?.label ?? "LightGBM"}</p>
        <OtherModels models={others} />
      </section>

      <section>
        <h2>Latest data used</h2>
        <dl>
          <dt>Weather</dt>
          <dd>{formatDate(result.weather_date)}</dd>
          <dt>Drought</dt>
          <dd>{formatDate(result.drought_date)}</dd>
        </dl>
      </section>

      {fire && (
        <section className="nearby">
          <h2>Nearby fire</h2>
          <p className="fire-name">
            {fire.name}
            {fire.state ? `, ${fire.state}` : ""}
            <span className="muted"> · {fire.distance_km} km away</span>
          </p>
          <dl>
            <dt>Discovered</dt>
            <dd>{formatDate(fire.discovered)}</dd>
            <dt>Contained</dt>
            <dd>{formatPercent(fire.percent_contained)}</dd>
            <dt>Reported size</dt>
            <dd>{formatAcres(fire.acres)}</dd>
            <dt>Spread rate so far</dt>
            <dd>{formatRate(fire.spread_so_far)}</dd>
          </dl>
          <FireCharts irwinId={fire.irwin_id} />
        </section>
      )}

      {result.notice && <p className="notice">{result.notice}</p>}
    </div>
  );
}
