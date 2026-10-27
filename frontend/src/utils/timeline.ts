/** Geological period definitions (ICS standard colors) and helpers. */

export interface GeoPeriod {
  name: string;
  nameCn: string;
  abbr: string;
  startMa: number; // older boundary
  endMa: number;   // younger boundary
  color: string;
}

export const GEO_PERIODS: GeoPeriod[] = [
  { name: "Carboniferous", nameCn: "石炭纪", abbr: "C", startMa: 358.9, endMa: 298.9, color: "#67a9cf" },
  { name: "Permian",       nameCn: "二叠纪", abbr: "P", startMa: 298.9, endMa: 251.9, color: "#f04028" },
  { name: "Triassic",      nameCn: "三叠纪", abbr: "T", startMa: 251.9, endMa: 201.4, color: "#812b92" },
  { name: "Jurassic",      nameCn: "侏罗纪", abbr: "J", startMa: 201.4, endMa: 145.0, color: "#34b2c9" },
  { name: "Cretaceous",    nameCn: "白垩纪", abbr: "K", startMa: 145.0, endMa: 66.0,  color: "#7fc64e" },
  { name: "Paleogene",     nameCn: "古近纪", abbr: "Pg",startMa: 66.0,  endMa: 23.0,  color: "#fd9a52" },
];

/** Map an age (Ma) to an x-coordinate within the given width. Older = right. */
export function ageToX(ageMa: number, width: number, minMa: number, maxMa: number): number {
  return width * (maxMa - ageMa) / (maxMa - minMa);
}
