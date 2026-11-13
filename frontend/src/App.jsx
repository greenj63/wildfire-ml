import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchFires, fetchPrediction } from "./api";
import CoordinateInput from "./components/CoordinateInput";
import FireMap from "./components/FireMap";
import Header from "./components/Header";
import Legend from "./components/Legend";
import ResultPanel from "./components/ResultPanel";
import { isMapped } from "./fireSize";

const FIRE_REFRESH_MS = 10 * 60 * 1000;

export default function App() {
  const [fires, setFires] = useState([]);
  const [firesLoaded, setFiresLoaded] = useState(false);
  const [firesError, setFiresError] = useState(null);

  const [selected, setSelected] = useState(null); // { lat, lon, fromInput }
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const controller = useRef(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchFires();
        if (cancelled) return;
        setFires(data.fires);
        setFiresLoaded(true);
        setFiresError(null);
      } catch (problem) {
        if (!cancelled) setFiresError(problem.message);
      }
    }
    load();
    const timer = setInterval(load, FIRE_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  // Used by map clicks, fire symbols and the coordinate box. A newer request replaces
  // an older one that is still running.
  const predict = useCallback(async (lat, lon, fromInput) => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;

    setSelected({ lat, lon, fromInput });
    setStatus("loading");
    try {
      const data = await fetchPrediction(lat, lon, current.signal);
      setResult(data);
      setStatus("done");
    } catch (problem) {
      if (problem.name === "AbortError") return;
      setError(problem.message);
      setStatus("error");
    }
  }, []);

  const mappedFires = useMemo(() => fires.filter(isMapped), [fires]);

  return (
    <main className="page">
      <Header />
      <div className="panels">
        <section className="card map-card">
          <div className="map-wrap">
            <FireMap fires={mappedFires} selected={selected} onSelect={(lat, lon) => predict(lat, lon, false)} />
          </div>
          <Legend count={firesLoaded ? mappedFires.length : null} error={firesError && "Could not load active fires."} />
        </section>

        <section className="card result-card">
          <CoordinateInput
            value={selected && !selected.fromInput ? selected : null}
            onSubmit={(lat, lon) => predict(lat, lon, true)}
          />
          <div className="result-body">
            <ResultPanel status={status} result={result} error={error} />
          </div>
        </section>
      </div>
    </main>
  );
}
