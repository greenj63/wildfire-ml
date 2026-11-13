// Only fires at least this big are drawn on the map.
export const MIN_FIRE_ACRES = 100;

// Fire symbol sizes. The map markers and the legend both use this, so they always agree.
export const SIZE_BUCKETS = [
  { min: 100, label: "100 to 499 acres", px: 20 },
  { min: 500, label: "500 to 1,999 acres", px: 28 },
  { min: 2000, label: "2,000 to 9,999 acres", px: 38 },
  { min: 10000, label: "10,000 to 49,999 acres", px: 50 },
  { min: 50000, label: "50,000 acres or more", px: 64 },
];

export function isMapped(fire) {
  return Number(fire.acres) >= MIN_FIRE_ACRES;
}

export function bucketIndex(acres) {
  const size = Number(acres) || 0;
  let index = 0;
  SIZE_BUCKETS.forEach((bucket, i) => {
    if (size >= bucket.min) index = i;
  });
  return index;
}

export function fireSizePx(acres) {
  return SIZE_BUCKETS[bucketIndex(acres)].px;
}
