import { useEffect, useRef, useState } from "react";

import Chart from "./Chart";

// A small preview that opens a larger chart in a dialog when clicked.
export default function ExpandableChart({ title, points, kind, color, unit, note }) {
  const [open, setOpen] = useState(false);
  const dialog = useRef(null);

  useEffect(() => {
    const element = dialog.current;
    if (open && element && !element.open) element.showModal();
  }, [open]);

  return (
    <>
      <button type="button" className="chart-thumb" onClick={() => setOpen(true)} aria-label={`${title}. Click to expand`}>
        <span className="chart-thumb-title">{title}</span>
        <Chart points={points} kind={kind} color={color} unit={unit} compact />
        <span className="chart-thumb-hint">Click to expand</span>
      </button>

      {open && (
        <dialog
          ref={dialog}
          className="chart-dialog"
          aria-label={title}
          onClose={() => setOpen(false)}
          onClick={(event) => {
            if (event.target === dialog.current) dialog.current.close(); // the dimmed backdrop
          }}
        >
          <div className="chart-dialog-head">
            <h3>{title}</h3>
            <button type="button" className="chart-close" onClick={() => dialog.current.close()} aria-label="Close">
              ×
            </button>
          </div>
          <Chart points={points} kind={kind} color={color} unit={unit} />
          {note && <p className="chart-note">{note}</p>}
        </dialog>
      )}
    </>
  );
}
