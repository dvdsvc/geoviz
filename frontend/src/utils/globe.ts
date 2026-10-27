/** D3-geo orthographic projection helpers for the 3D globe. */

import { geoOrthographic, geoGraticule, GeoProjection, GeoGraticuleGenerator } from "d3-geo";

export function createGlobeProjection(width: number, height: number): GeoProjection {
  return geoOrthographic()
    .scale(Math.min(width, height) / 2.2)
    .translate([width / 2, height / 2])
    .clipAngle(90);
}

export function createGraticule(): GeoGraticuleGenerator {
  return geoGraticule().step([15, 15]);
}
