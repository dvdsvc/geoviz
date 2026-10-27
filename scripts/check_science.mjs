// Run with Node 24+; native TypeScript stripping loads the preserved utilities.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { weightedMean, peakAge, minApparentAge } from '../frontend/src/utils/spotCalc.ts';
import { concordiaPoint } from '../frontend/src/utils/concordia.ts';

const rows = JSON.parse(readFileSync(new URL('../frontend/src/data/realSpots.json', import.meta.url)));
const spots = rows.filter(s => s.sample_id === 'DEMO01');
const result = weightedMean(spots);
assert.equal(result.n, 6);
assert.equal(result.mean, 103);
assert.equal(result.error, 0.5774);
assert.equal(result.mswd, 6.2);
const peak = peakAge(spots);
assert.equal(peak.curve.length, 201);
assert.ok(Number.isFinite(peak.peakDensity) && peak.peakDensity > 0);
assert.ok(Math.abs(peak.peakAge - 105) < 0.2);
const youngest = minApparentAge(spots);
assert.equal(youngest.age, 100);
for (const age of [0,50,100,200,350]) {
  const point = concordiaPoint(age);
  assert.ok(Math.abs(Math.log1p(point.x)/1.55125e-10/1e6-age)<1e-8);
  assert.ok(Math.abs(Math.log1p(point.y)/9.8485e-10/1e6-age)<1e-8);
}
console.log(JSON.stringify({input:'six synthetic DEMO01 spots', weighted_mean:result,
  peak_age:peak.peakAge, concordia_round_trip_ages:[0,50,100,200,350],
  youngest_apparent_age:youngest.age, passed:true},null,2));
