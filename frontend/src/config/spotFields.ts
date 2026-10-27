/**
 * Spot field configuration — SINGLE SOURCE OF TRUTH.
 *
 * To add/rename fields: edit SPOT_FIELDS below.
 * Backend CSV column names must match `key` values.
 * Frontend tables, formatters, and calculations all read from here.
 */

export interface SpotFieldDef {
  key: string;           // object key (dot path for nested fields)
  label: string;         // Display name
  type: "number" | "string";
  calcGroup?: "age" | "ratio" | "quality" | "geochem";
  format?: (v: unknown) => string;
  width?: number;        // px, for table columns
}

/** Helper: access nested field by dot-path, e.g. "r206_238.value" */
function getNested(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const seg of path.split(".")) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[seg];
  }
  return cur;
}

export const SPOT_FIELDS: SpotFieldDef[] = [
  {
    key: "spot_id",
    label: "Spot #",
    type: "string",
    width: 65,
  },
  // ── Geochemistry ──
  {
    key: "u_ppm",
    label: "U (ppm)",
    type: "number",
    calcGroup: "geochem",
    width: 72,
    format: (v) => (v != null ? Number(v).toFixed(0) : "—"),
  },
  {
    key: "th_ppm",
    label: "Th (ppm)",
    type: "number",
    calcGroup: "geochem",
    width: 72,
    format: (v) => (v != null ? Number(v).toFixed(0) : "—"),
  },
  {
    key: "th_u_ratio",
    label: "Th/U",
    type: "number",
    calcGroup: "geochem",
    width: 60,
    format: (v) => (v != null ? Number(v).toFixed(3) : "—"),
  },
  // ── Isotope ratios ──
  {
    key: "r206_238_val",
    label: "²⁰⁶Pb/²³⁸U",
    type: "number",
    calcGroup: "ratio",
    width: 90,
    format: (v) => (v != null ? Number(v).toPrecision(6) : "—"),
  },
  {
    key: "r206_238_err",
    label: "²⁰⁶/²³⁸ ±1σ",
    type: "number",
    calcGroup: "ratio",
    width: 72,
    format: (v) => (v != null ? Number(v).toPrecision(4) : "—"),
  },
  {
    key: "r207_235_val",
    label: "²⁰⁷Pb/²³⁵U",
    type: "number",
    calcGroup: "ratio",
    width: 90,
    format: (v) => (v != null ? Number(v).toPrecision(6) : "—"),
  },
  {
    key: "r207_235_err",
    label: "²⁰⁷/²³⁵ ±1σ",
    type: "number",
    calcGroup: "ratio",
    width: 72,
    format: (v) => (v != null ? Number(v).toPrecision(4) : "—"),
  },
  {
    key: "r207_206_val",
    label: "²⁰⁷Pb/²⁰⁶Pb",
    type: "number",
    calcGroup: "ratio",
    width: 90,
    format: (v) => (v != null ? Number(v).toPrecision(6) : "—"),
  },
  {
    key: "r207_206_err",
    label: "²⁰⁷/²⁰⁶ ±1σ",
    type: "number",
    calcGroup: "ratio",
    width: 72,
    format: (v) => (v != null ? Number(v).toPrecision(4) : "—"),
  },
  // ── Ages ──
  {
    key: "age_206_238_val",
    label: "²⁰⁶Pb/²³⁸U Age",
    type: "number",
    calcGroup: "age",
    width: 100,
    format: (v) => (v != null ? Number(v).toFixed(2) : "—"),
  },
  {
    key: "age_206_238_err",
    label: "±1σ",
    type: "number",
    calcGroup: "age",
    width: 60,
    format: (v) => (v != null ? Number(v).toFixed(2) : "—"),
  },
  {
    key: "age_207_235_val",
    label: "²⁰⁷Pb/²³⁵U Age",
    type: "number",
    calcGroup: "age",
    width: 100,
    format: (v) => (v != null ? Number(v).toFixed(2) : "—"),
  },
  {
    key: "age_207_235_err",
    label: "±1σ",
    type: "number",
    calcGroup: "age",
    width: 60,
    format: (v) => (v != null ? Number(v).toFixed(2) : "—"),
  },
  // ── Quality ──
  {
    key: "concordance",
    label: "Conc. %",
    type: "number",
    calcGroup: "quality",
    width: 65,
    format: (v) => (v != null ? Number(v).toFixed(1) : "—"),
  },
];

/** Read a field value from a spot record, supporting dot-path keys. */
export function getFieldValue(spot: Record<string, unknown>, key: string): unknown {
  return key.includes(".") ? getNested(spot, key) : spot[key];
}

// ── Calculation Methods ──────────────────────────────────────────────────────

export type CalcMethod = "weightedMean" | "peakAge" | "minApparentAge";

/**
 * Isotope system → allowed calculation methods.
 * Derived from chain_rules.txt (Layer 2 + R12).
 *
 * To add a new isotope system or method: edit this map.
 */
export const ISOTOPE_SYSTEM_CALC_MAP: Record<string, CalcMethod[]> = {
  "U-Th-Pb": ["weightedMean", "peakAge", "minApparentAge"],
  "K-Ar":    ["weightedMean"],
  "Ar-Ar":   ["weightedMean"],
  "Rb-Sr":   ["weightedMean"],
  "Sm-Nd":   ["weightedMean"],
  "Re-Os":   ["weightedMean"],
  "Lu-Hf":   ["weightedMean"],
};

export const CALC_METHOD_INFO: Record<CalcMethod, { label: string; labelEn: string; description: string }> = {
  weightedMean: {
    label: "加权平均",
    labelEn: "Weighted Mean",
    description: "误差倒数平方加权，输出 weighted mean ± error + MSWD",
  },
  peakAge: {
    label: "KDE 峰值",
    labelEn: "KDE Peak Age",
    description: "核密度估计主峰年龄，适用于碎屑锆石/MDA 年龄谱",
  },
  minApparentAge: {
    label: "最小表观年龄",
    labelEn: "Min Apparent Age",
    description: "满足谐和度要求的最小单点年龄",
  },
};

/** Get allowed calc methods for a given isotope system. Falls back to weightedMean only. */
export function getAllowedCalcMethods(isotopeSystem: string | null | undefined): CalcMethod[] {
  if (!isotopeSystem) return ["weightedMean"];
  return ISOTOPE_SYSTEM_CALC_MAP[isotopeSystem] ?? ["weightedMean"];
}
