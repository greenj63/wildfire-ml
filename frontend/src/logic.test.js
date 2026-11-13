import assert from "node:assert/strict";
import { test } from "node:test";

import { niceTicks, nearestIndex, toPoints } from "./chartMath.js";
import { parseCoordinates } from "./coords.js";
import { bucketIndex, fireSizePx, isMapped, MIN_FIRE_ACRES, SIZE_BUCKETS } from "./fireSize.js";
import { formatAcres, formatDate, formatPercent, formatRate } from "./format.js";

test("coordinates are parsed in the common formats", () => {
  for (const text of ["38.94, -123.32", "(38.94, -123.32)", " 38.94 -123.32 ", "38.94,-123.32"]) {
    assert.deepEqual(parseCoordinates(text), { lat: 38.94, lon: -123.32 }, text);
  }
});

test("bad coordinates are rejected with a message", () => {
  assert.ok(parseCoordinates("hello").error);
  assert.ok(parseCoordinates("38.94").error);
  assert.match(parseCoordinates("10, 10").error, /continental US/);
  assert.match(parseCoordinates("38.94, 123.32").error, /continental US/); // east, not west
});

test("fire sizes fall into the legend buckets", () => {
  assert.equal(bucketIndex(100), 0);
  assert.equal(bucketIndex(499), 0);
  assert.equal(bucketIndex(500), 1);
  assert.equal(bucketIndex(1999), 1);
  assert.equal(bucketIndex(2000), 2);
  assert.equal(bucketIndex(10000), 3);
  assert.equal(bucketIndex(49999), 3);
  assert.equal(bucketIndex(102007), 4);
  assert.equal(fireSizePx(250000), SIZE_BUCKETS[4].px);
});

test("only fires of 100 acres or more are mapped", () => {
  assert.equal(MIN_FIRE_ACRES, 100);
  assert.equal(SIZE_BUCKETS[0].min, MIN_FIRE_ACRES);
  assert.equal(isMapped({ acres: 100 }), true);
  assert.equal(isMapped({ acres: 99.9 }), false);
  assert.equal(isMapped({ acres: null }), false);
  assert.equal(isMapped({}), false);
});

test("symbols grow with the fire", () => {
  const sizes = SIZE_BUCKETS.map((bucket) => bucket.px);
  assert.deepEqual(sizes, [...sizes].sort((a, b) => a - b));
  assert.equal(new Set(sizes).size, sizes.length);
});

test("chart ticks cover the data", () => {
  assert.deepEqual(niceTicks(0), [0, 1]);
  const ticks = niceTicks(7359);
  assert.equal(ticks[0], 0);
  assert.ok(ticks.at(-1) >= 7359);
  assert.ok(ticks.length <= 7);
  assert.deepEqual(niceTicks(950, 4), [0, 250, 500, 750, 1000]);
});

test("chart hover picks the nearest day", () => {
  assert.equal(nearestIndex([0, 10, 20], 12), 1);
  assert.equal(nearestIndex([0, 10, 20], 99), 2);
});

test("chart points skip days without a value", () => {
  const series = [
    { date: "2026-07-01", acres: 10, rate: null },
    { date: "2026-07-02", acres: 30, rate: 20 },
  ];
  assert.equal(toPoints(series, "acres").length, 2);
  assert.deepEqual(toPoints(series, "rate"), [{ x: Date.UTC(2026, 6, 2), y: 20 }]);
});

test("formatting", () => {
  assert.equal(formatPercent(92), "92%");
  assert.equal(formatPercent(null), "Not reported");
  assert.equal(formatDate("2026-11-10"), "Nov 10, 2026");
  assert.equal(formatDate(null), "Not available");
  assert.equal(formatAcres(61380), "61,380 acres");
  assert.equal(formatAcres(null), "Not reported");
  assert.equal(formatRate(515.8), "515.8 acres/day");
  assert.equal(formatRate(0.236), "0.24 acres/day");
});
