// The fire symbol, drawn as SVG so no image file is needed. Used by the map and legend.
export default function FlameIcon({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 1C12 1 18.5 7 18.5 13.5A6.5 6.5 0 0 1 5.5 13.5C5.5 10.5 7.2 8.6 8.3 7.5C8.4 9.6 9.3 10.6 10.2 10.9C9.6 7.5 10.6 3.6 12 1Z"
        fill="#f0531c"
        stroke="#b83a0e"
        strokeWidth="0.8"
        strokeLinejoin="round"
      />
      <path
        d="M12 20A3.6 3.6 0 0 1 8.4 16.4C8.4 14.6 9.6 13.5 10.6 12.6C10.9 14 11.6 14.6 12.3 14.9C12.9 14 13.2 13 13.1 12.2C14.4 13.3 15.6 14.7 15.6 16.4A3.6 3.6 0 0 1 12 20Z"
        fill="#ffc933"
      />
    </svg>
  );
}
