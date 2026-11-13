import { useEffect, useState } from "react";

import { formatCoordinates, parseCoordinates } from "../coords";

// `value` is the last point chosen on the map; typing is allowed any time.
export default function CoordinateInput({ value, disabled, onSubmit }) {
  const [text, setText] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (value) {
      setText(formatCoordinates(value.lat, value.lon));
      setError(null);
    }
  }, [value]);

  function submit(event) {
    event.preventDefault();
    const parsed = parseCoordinates(text);
    if (parsed.error) {
      setError(parsed.error);
      return;
    }
    setError(null);
    onSubmit(parsed.lat, parsed.lon);
  }

  return (
    <form className="coord-form" onSubmit={submit}>
      <input
        className="coord-input"
        type="text"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Enter coordinates [ex: (38.94, -123.32)]"
        aria-label="Coordinates (latitude, longitude)"
        aria-invalid={Boolean(error)}
        autoComplete="off"
        spellCheck="false"
        disabled={disabled}
      />
      <button className="coord-button" type="submit" disabled={disabled || !text.trim()}>
        Predict
      </button>
      {error && (
        <p className="coord-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
