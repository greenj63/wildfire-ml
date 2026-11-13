const dateFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

// "2026-11-10" -> "Nov 10, 2026". Read as UTC so the day never shifts with time zones.
export function formatDate(isoDate) {
  if (!isoDate) return "Not available";
  const date = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? "Not available" : dateFormat.format(date);
}

export function formatAcres(acres) {
  if (acres === null || acres === undefined) return "Not reported";
  return `${Number(acres).toLocaleString("en-US", { maximumFractionDigits: 1 })} acres`;
}

export function formatRate(rate) {
  if (rate === null || rate === undefined) return "Not available";
  return `${Number(rate).toLocaleString("en-US", { maximumFractionDigits: 2 })} acres/day`;
}

export function formatPercent(percent) {
  if (percent === null || percent === undefined) return "Not reported";
  return `${Math.round(Number(percent))}%`;
}
