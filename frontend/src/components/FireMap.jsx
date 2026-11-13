import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";

import { bucketIndex, SIZE_BUCKETS } from "../fireSize";
import { formatAcres } from "../format";
import FlameIcon from "./FlameIcon";

const US_BOUNDS = [
  [24, -125],
  [50, -66],
];
const PAN_LIMITS = [
  [14, -140],
  [58, -55],
];

// One icon per size bucket, shared by every fire in that bucket
function buildIcons() {
  return SIZE_BUCKETS.map((bucket) =>
    L.divIcon({
      className: "fire-icon",
      html: renderToStaticMarkup(<FlameIcon size={bucket.px} />),
      iconSize: [bucket.px, bucket.px],
      iconAnchor: [bucket.px / 2, bucket.px / 2],
    }),
  );
}

function ClickHandler({ onSelect }) {
  useMapEvents({
    click(event) {
      onSelect(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

// Pans to coordinates typed into the box (clicks on the map already show where they are)
function Follow({ target }) {
  const map = useMap();
  useEffect(() => {
    if (target?.fromInput) map.flyTo([target.lat, target.lon], Math.max(map.getZoom(), 6));
  }, [map, target]);
  return null;
}

export default function FireMap({ fires, selected, onSelect }) {
  const icons = useMemo(buildIcons, []);

  return (
    <MapContainer
      className="map"
      bounds={US_BOUNDS}
      boundsOptions={{ padding: [8, 8] }}
      zoomSnap={0.25}
      minZoom={3}
      maxBounds={PAN_LIMITS}
      maxBoundsViscosity={0.8}
      worldCopyJump={false}
    >
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        attribution="Tiles &copy; Esri, HERE, Garmin, OpenStreetMap contributors"
        maxNativeZoom={16}
      />
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
        maxNativeZoom={16}
      />
      <ClickHandler onSelect={onSelect} />
      <Follow target={selected} />
      {fires.map((fire, index) => {
        const bucket = bucketIndex(fire.acres);
        return (
          <Marker
            key={`${fire.name}-${index}`}
            position={[fire.latitude, fire.longitude]}
            icon={icons[bucket]}
            zIndexOffset={-bucket * 100} // small fires stay on top, so they stay clickable
            eventHandlers={{ click: () => onSelect(fire.latitude, fire.longitude) }}
          >
            <Tooltip direction="top" offset={[0, -SIZE_BUCKETS[bucket].px / 2]}>
              <strong>{fire.name}</strong>
              <br />
              {formatAcres(fire.acres)}
            </Tooltip>
          </Marker>
        );
      })}
      {selected && (
        <CircleMarker
          center={[selected.lat, selected.lon]}
          radius={7}
          pathOptions={{ color: "#111", weight: 3, fillColor: "#fff", fillOpacity: 0.9 }}
          interactive={false}
        />
      )}
    </MapContainer>
  );
}
