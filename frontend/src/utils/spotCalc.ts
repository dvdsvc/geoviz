/**
 * Spot age calculation algorithms.
 *
 * All methods take an array of spots that have already been filtered
 * (s_discarded removed by caller). Single source of truth: realSpots.json
 */

export interface SpotRecord {
  spot_id: string;
  sample_id: string;
  s_discarded: boolean;
  u_ppm?: number | null;
  th_ppm?: number | null;
  th_u_ratio?: number | null;
  r206_238_val?: number | null;
  r206_238_err?: number | null;
  r207_235_val?: number | null;
  r207_235_err?: number | null;
  r207_206_val?: number | null;
  r207_206_err?: number | null;
  age_206_238_val?: number | null;
  age_206_238_err?: number | null;
  age_207_235_val?: number | null;
  age_207_235_err?: number | null;
  concordance?: number | null;
  [key: string]: unknown;
}

export interface WeightedMeanResult {
  method: "weightedMean";
  mean: number;
  error: number;
  mswd: number;
  n: number;
}

export interface PeakAgeResult {
  method: "peakAge";
  peakAge: number;
  peakDensity: number;
  n: number;
  curve: [number, number][];
}

export interface MinApparentAgeResult {
  method: "minApparentAge";
  age: number;
  error: number;
  grainId: string;
  concordance: number;
  n: number;
}

export type CalcResult = WeightedMeanResult | PeakAgeResult | MinApparentAgeResult;

// ── Helper: Get age from spot (prefer 206/238, fallback to 207/235) ──
function getAge(s: SpotRecord): { age: number; error: number } | null {
  if (s.age_206_238_val != null && s.age_206_238_err != null) {
    return { age: s.age_206_238_val, error: s.age_206_238_err };
  }
  if (s.age_207_235_val != null && s.age_207_235_err != null) {
    return { age: s.age_207_235_val, error: s.age_207_235_err };
  }
  return null;
}

// ── 1. Weighted Mean ────────────────────────────────────────────────────────
// Inverse-variance weighted average + MSWD

export function weightedMean(spots: SpotRecord[]): WeightedMeanResult {
  const withAge = spots
    .map((s) => ({ s, a: getAge(s) }))
    .filter((x) => x.a !== null) as { s: SpotRecord; a: { age: number; error: number } }[];

  const n = withAge.length;
  if (n === 0) {
    return { method: "weightedMean", mean: 0, error: 0, mswd: 0, n: 0 };
  }

  // Weighted mean calculation
  let wSum = 0;
  let wTotal = 0;
  for (const { a } of withAge) {
    const w = 1 / (a.error * a.error);
    wSum += w * a.age;
    wTotal += w;
  }
  const mean = wSum / wTotal;
  const error = 1 / Math.sqrt(wTotal);

  // MSWD (Mean Square Weighted Deviation)
  let chi2 = 0;
  for (const { a } of withAge) {
    const w = 1 / (a.error * a.error);
    chi2 += w * (a.age - mean) ** 2;
  }
  const mswd = n > 1 ? chi2 / (n - 1) : 0;

  return {
    method: "weightedMean",
    mean: round(mean, 4),
    error: round(error, 4),
    mswd: round(mswd, 4),
    n,
  };
}

// ── 2. Peak Age (KDE) ──────────────────────────────────────────────────────
// Kernel density estimation peak

export function peakAge(spots: SpotRecord[]): PeakAgeResult {
  const ages = spots
    .map((s) => getAge(s))
    .filter(Boolean)
    .map((a) => a!.age)
    .sort((a, b) => a - b);

  const n = ages.length;
  if (n === 0) {
    return { method: "peakAge", peakAge: 0, peakDensity: 0, n: 0, curve: [] };
  }

  // Bandwidth (Silverman's rule)
  const mean = ages.reduce((a, b) => a + b, 0) / n;
  const variance = ages.reduce((sum, a) => sum + (a - mean) ** 2, 0) / (n - 1);
  const std = Math.sqrt(variance);
  const iqr = percentile(ages, 75) - percentile(ages, 25);
  const bandwidth = Math.max(0.9 * Math.min(std, iqr / 1.34) * Math.pow(n, -0.2), std * 0.5 || 1);

  // Evaluate KDE on grid
  const minAge = ages[0] - 3 * bandwidth;
  const maxAge = ages[n - 1] + 3 * bandwidth;
  const steps = 200;
  const stepSize = (maxAge - minAge) / steps;

  let peakAgeVal = ages[0];
  let peakDensity = 0;
  const curve: [number, number][] = [];

  for (let i = 0; i <= steps; i++) {
    const x = minAge + i * stepSize;
    let density = 0;
    for (const a of ages) {
      const u = (x - a) / bandwidth;
      density += Math.exp(-0.5 * u * u);
    }
    density /= n * bandwidth * Math.sqrt(2 * Math.PI);
    curve.push([round(x, 2), density]);

    if (density > peakDensity) {
      peakDensity = density;
      peakAgeVal = x;
    }
  }

  return {
    method: "peakAge",
    peakAge: round(peakAgeVal, 2),
    peakDensity,
    n,
    curve,
  };
}

// ── 3. Minimum Apparent Age ─────────────────────────────────────────────────
// Youngest concordant spot (90–110% concordance)

export function minApparentAge(spots: SpotRecord[]): MinApparentAgeResult {
  const withAge = spots
    .map((s) => ({ s, a: getAge(s) }))
    .filter((x) => x.a !== null) as { s: SpotRecord; a: { age: number; error: number } }[];

  // Filter to concordant spots
  const concordant = withAge.filter(
    ({ s }) => s.concordance != null && s.concordance >= 90 && s.concordance <= 110
  );

  const pool = concordant.length > 0 ? concordant : withAge;
  if (pool.length === 0) {
    return { method: "minApparentAge", age: 0, error: 0, grainId: "", concordance: 0, n: 0 };
  }

  const youngest = [...pool].sort((a, b) => a.a.age - b.a.age)[0];

  return {
    method: "minApparentAge",
    age: round(youngest.a.age, 2),
    error: round(youngest.a.error, 2),
    grainId: youngest.s.spot_id,
    concordance: youngest.s.concordance ?? 0,
    n: withAge.length,
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function percentile(sorted: number[], p: number): number {
  const idx = (p / 100) * (sorted.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

function round(v: number, decimals: number): number {
  const f = 10 ** decimals;
  return Math.round(v * f) / f;
}
