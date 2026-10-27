/** Wetherill U-Pb concordia utilities. */

const LAMBDA_238 = 1.55125e-10;
const LAMBDA_235 = 9.8485e-10;

/** Concordia point at a given age (Ma). Returns {x: 206Pb/238U, y: 207Pb/235U}. */
export function concordiaPoint(ageMa: number): { x: number; y: number } {
  const t = ageMa * 1e6;
  return {
    x: Math.exp(LAMBDA_238 * t) - 1,
    y: Math.exp(LAMBDA_235 * t) - 1,
  };
}

/** Generate the concordia curve as an array of points from 0 to maxAge Ma. */
export function concordiaCurve(maxAge: number = 400, step: number = 1): Array<{ x: number; y: number }> {
  const pts: Array<{ x: number; y: number }> = [];
  for (let age = 0; age <= maxAge; age += step) {
    pts.push(concordiaPoint(age));
  }
  return pts;
}
