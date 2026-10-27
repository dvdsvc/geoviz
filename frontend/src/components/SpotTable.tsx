"use client";

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { X, Check, Minus, AlertTriangle } from "lucide-react";
import { Sample } from "@/types";
import { SpotRecord, weightedMean, peakAge, minApparentAge, CalcResult } from "@/utils/spotCalc";
import { SPOT_FIELDS, CalcMethod, getAllowedCalcMethods, CALC_METHOD_INFO, getFieldValue } from "@/config/spotFields";
import { concordiaPoint, concordiaCurve } from "@/utils/concordia";

interface SpotTableProps {
  sample: Sample;
  spots: SpotRecord[];
  onClose: () => void;
  onUpdateSpots: (sampleId: string, spots: SpotRecord[]) => void;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

const CONCORDANCE_MIN = 90;
const CONCORDANCE_MAX = 110;

export default function SpotTable({ sample, spots, onClose, onUpdateSpots }: SpotTableProps) {
  const color = regionColors[sample.region] || "#007aff";
  const tableRowRefs = useRef<Map<string, HTMLTableRowElement>>(new Map());

  // ── State ──
  const allowedMethods = useMemo(() => getAllowedCalcMethods(sample.datingSystem), [sample.datingSystem]);
  const [activeMethod, setActiveMethod] = useState<CalcMethod>(allowedMethods[0]);
  const [hoveredSpotId, setHoveredSpotId] = useState<string | null>(null);
  const [concRange, setConcRange] = useState<[number, number]>([0, 200]);

  // ── Derived: spots filtered by concordance ──
  const concordanceFiltered = useMemo(() => {
    return spots.map((s) => {
      const c = s.concordance ?? 100;
      const inRange = c >= concRange[0] && c <= concRange[1];
      return { ...s, _inConcRange: inRange };
    }) as (SpotRecord & { _inConcRange: boolean })[];
  }, [spots, concRange]);

  // Active = not discarded AND in concordance range (used for visualization highlighting)
  const activeSpots = useMemo(
    () => concordanceFiltered.filter((s) => !s.s_discarded && s._inConcRange),
    [concordanceFiltered]
  );

  // Included = not discarded (used for calculations, not affected by concordance range)
  const includedSpots = useMemo(
    () => spots.filter((s) => !s.s_discarded),
    [spots]
  );

  const includedCount = useMemo(() => includedSpots.length, [includedSpots]);

  // ── Concordia chart data ──
  const concordiaData = useMemo(() => {
    const curve = concordiaCurve(400, 1);
    const mapped = concordanceFiltered
      .filter((s) => !s.s_discarded && s.r206_238_val != null && s.r207_235_val != null)
      .map((s) => ({
        spotId: s.spot_id,
        x: s.r206_238_val!,
        y: s.r207_235_val!,
        concordance: s.concordance ?? 0,
        age: s.age_206_238_val ?? 0,
        active: s._inConcRange,
      }));

    const ageMa = sample.ageMa ?? 150;
    const meanPt = concordiaPoint(ageMa);

    const allX = [...curve.map((p) => p.x), ...mapped.map((g) => g.x), meanPt.x];
    const allY = [...curve.map((p) => p.y), ...mapped.map((g) => g.y), meanPt.y];
    return {
      curve,
      grains: mapped,
      meanPoint: meanPt,
      xDomain: [Math.min(...allX) * 0.92, Math.max(...allX) * 1.08] as [number, number],
      yDomain: [Math.min(...allY) * 0.92, Math.max(...allY) * 1.08] as [number, number],
    };
  }, [concordanceFiltered, sample]);

  // ── Visible columns ──
  const visibleFields = useMemo(
    () => SPOT_FIELDS.filter((f) => spots.some((s) => {
      const v = getFieldValue(s as unknown as Record<string, unknown>, f.key);
      return v !== null && v !== undefined && v !== "";
    })),
    [spots]
  );

  // ── Actions ──
  const toggleSpot = useCallback(
    (spotId: string) => {
      const next = spots.map((s) =>
        s.spot_id === spotId ? { ...s, s_discarded: !s.s_discarded } : s
      );
      onUpdateSpots(sample.sampleId, next);
    },
    [spots, sample.sampleId, onUpdateSpots]
  );

  const selectAll = useCallback(() => {
    onUpdateSpots(sample.sampleId, spots.map((s) => ({ ...s, s_discarded: false })));
  }, [spots, sample.sampleId, onUpdateSpots]);

  const clearAll = useCallback(() => {
    onUpdateSpots(sample.sampleId, spots.map((s) => ({ ...s, s_discarded: true })));
  }, [spots, sample.sampleId, onUpdateSpots]);

  const excludeDiscordant = useCallback(() => {
    onUpdateSpots(sample.sampleId, spots.map((s) => ({
      ...s,
      s_discarded: s.concordance != null
        ? !(s.concordance >= CONCORDANCE_MIN && s.concordance <= CONCORDANCE_MAX)
        : false,
    })));
  }, [spots, sample.sampleId, onUpdateSpots]);

  const scrollToRow = useCallback((spotId: string) => {
    const el = tableRowRefs.current.get(spotId);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  // ── Calculation ──
  const result: CalcResult = useMemo(() => {
    const pool = includedSpots as SpotRecord[];
    switch (activeMethod) {
      case "weightedMean": return weightedMean(pool);
      case "peakAge": return peakAge(pool);
      case "minApparentAge": return minApparentAge(pool);
    }
  }, [includedSpots, activeMethod]);

  // ── Concordia SVG ──
  const W = 380, H = 260;
  const PAD = { top: 12, right: 12, bottom: 36, left: 44 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const { curve, grains, meanPoint, xDomain, yDomain } = concordiaData;

  const scaleX = (v: number) => PAD.left + (v - xDomain[0]) / (xDomain[1] - xDomain[0]) * plotW;
  const scaleY = (v: number) => PAD.top + plotH - (v - yDomain[0]) / (yDomain[1] - yDomain[0]) * plotH;

  const curvePath = curve
    .map((p, i) => `${i === 0 ? "M" : "L"}${scaleX(p.x).toFixed(2)},${scaleY(p.y).toFixed(2)}`)
    .join(" ");
  const labelAges = [50, 100, 150, 200, 250, 300, 350];

  return (
    <div className="ios-card overflow-hidden flex flex-col" style={{ width: 420, maxHeight: "90vh" }}>
      {/* Header */}
      <div className="px-4 pt-3 pb-1 flex items-center justify-between flex-shrink-0">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label">
            Spot Analysis
          </span>
          <h3 className="text-[15px] font-semibold text-foreground mt-0.5 flex items-center gap-2">
            {sample.sampleId}
            {sample.datingSystem && (
              <span className="text-[11px] font-normal px-2 py-0.5 rounded-full bg-black/5 text-secondary-label">
                {sample.datingSystem}
              </span>
            )}
          </h3>
        </div>
        <button onClick={onClose}
          className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10">
          <X className="w-3.5 h-3.5 text-secondary-label" />
        </button>
      </div>

      {/* Concordia chart */}
      <div className="px-3 pt-1 pb-1 flex-shrink-0">
        <svg width={W} height={H} className="block mx-auto">
          {/* Grid */}
          {Array.from({ length: 6 }, (_, i) => {
            const v = xDomain[0] + (i / 5) * (xDomain[1] - xDomain[0]);
            return <line key={`gx-${i}`} x1={scaleX(v)} y1={PAD.top} x2={scaleX(v)} y2={PAD.top + plotH}
              stroke="rgba(0,0,0,0.04)" strokeWidth={0.5} />;
          })}
          {Array.from({ length: 6 }, (_, i) => {
            const v = yDomain[0] + (i / 5) * (yDomain[1] - yDomain[0]);
            return <line key={`gy-${i}`} x1={PAD.left} y1={scaleY(v)} x2={PAD.left + plotW} y2={scaleY(v)}
              stroke="rgba(0,0,0,0.04)" strokeWidth={0.5} />;
          })}

          <path d={curvePath} fill="none" stroke="#1c1c1e" strokeWidth={1.5} opacity={0.25} />

          {labelAges.map((age) => {
            const pt = concordiaPoint(age);
            const x = scaleX(pt.x), y = scaleY(pt.y);
            if (x < PAD.left || x > PAD.left + plotW || y < PAD.top || y > PAD.top + plotH) return null;
            return <text key={age} x={x + 4} y={y - 4}
              style={{ fontSize: 8, fill: "rgba(60,60,67,0.35)", fontFamily: "Inter, sans-serif" }}>{age}</text>;
          })}

          {/* Grains */}
          {grains.map((g) => {
            const isHovered = hoveredSpotId === g.spotId;
            const r = isHovered ? 5 : 3.5;
            const opacity = g.active ? (isHovered ? 1 : 0.7) : 0.2;
            const fill = g.active
              ? (g.concordance >= 95 && g.concordance <= 105 ? color
                : g.concordance >= 90 && g.concordance <= 110 ? "#e9c46a" : "#e63946")
              : "#999";
            return (
              <circle key={g.spotId} cx={scaleX(g.x)} cy={scaleY(g.y)} r={r}
                fill={fill} opacity={opacity} stroke="white" strokeWidth={isHovered ? 2 : 0.6}
                style={{ cursor: "pointer", transition: "r 0.15s, opacity 0.15s" }}
                onClick={() => { toggleSpot(g.spotId); scrollToRow(g.spotId); }}
                onMouseEnter={() => { setHoveredSpotId(g.spotId); scrollToRow(g.spotId); }}
                onMouseLeave={() => setHoveredSpotId(null)}
              >
                <title>{g.spotId}: {g.age.toFixed(1)} Ma, {g.concordance.toFixed(0)}% conc.</title>
              </circle>
            );
          })}

          {/* Mean point */}
          <circle cx={scaleX(meanPoint.x)} cy={scaleY(meanPoint.y)} r={5.5}
            fill={color} stroke="white" strokeWidth={2} />

          {/* Axes */}
          <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + plotH} stroke="rgba(0,0,0,0.12)" strokeWidth={1} />
          <line x1={PAD.left} y1={PAD.top + plotH} x2={PAD.left + plotW} y2={PAD.top + plotH} stroke="rgba(0,0,0,0.12)" strokeWidth={1} />

          {Array.from({ length: 5 }, (_, i) => {
            const v = xDomain[0] + ((i + 1) / 5) * (xDomain[1] - xDomain[0]);
            return <text key={`tx-${i}`} x={scaleX(v)} y={PAD.top + plotH + 14} textAnchor="middle"
              style={{ fontSize: 9, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>{v.toFixed(3)}</text>;
          })}
          {Array.from({ length: 5 }, (_, i) => {
            const v = yDomain[0] + ((i + 1) / 5) * (yDomain[1] - yDomain[0]);
            return <text key={`ty-${i}`} x={PAD.left - 6} y={scaleY(v) + 3} textAnchor="end"
              style={{ fontSize: 9, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>{v.toFixed(2)}</text>;
          })}

          <text x={PAD.left + plotW / 2} y={H - 4} textAnchor="middle"
            style={{ fontSize: 10, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>²⁰⁶Pb/²³⁸U</text>
          <text x={12} y={PAD.top + plotH / 2} textAnchor="middle"
            transform={`rotate(-90, 12, ${PAD.top + plotH / 2})`}
            style={{ fontSize: 10, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>²⁰⁷Pb/²³⁵U</text>
        </svg>

        {/* Legend + tip */}
        <div className="flex items-center justify-between px-2 mt-0.5">
          <div className="flex items-center gap-3 text-[9px] text-tertiary-label">
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: color }} /> Concordant</span>
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#e9c46a" }} /> ±10%</span>
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#e63946" }} /> Discordant</span>
          </div>
          <span className="text-[9px] text-tertiary-label">Click dot → toggle · Hover → locate</span>
        </div>
      </div>

      {/* Concordance slider */}
      <div className="px-4 py-1.5 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-tertiary-label flex-shrink-0">Conc.</span>
          <input
            type="range" min={0} max={200} value={concRange[0]}
            onChange={(e) => setConcRange([Math.min(Number(e.target.value), concRange[1] - 1), concRange[1]])}
            className="flex-1 h-1 accent-accent"
            style={{ margin: 0 }}
          />
          <input
            type="range" min={0} max={200} value={concRange[1]}
            onChange={(e) => setConcRange([concRange[0], Math.max(Number(e.target.value), concRange[0] + 1)])}
            className="flex-1 h-1 accent-accent"
            style={{ margin: 0, marginLeft: -4 }}
          />
          <span className="text-[10px] font-medium text-secondary-label flex-shrink-0 w-[60px] text-right">
            {concRange[0]}–{concRange[1]}%
          </span>
        </div>
      </div>

      {/* Quick actions + count */}
      <div className="px-4 pb-1.5 flex items-center justify-between flex-shrink-0">
        <div className="flex gap-1.5">
          <button onClick={selectAll}
            className="px-2 py-1 text-[10px] rounded-md bg-grouped-bg text-secondary-label hover:bg-black/5">All</button>
          <button onClick={clearAll}
            className="px-2 py-1 text-[10px] rounded-md bg-grouped-bg text-secondary-label hover:bg-black/5">None</button>
          {sample.datingSystem === "U-Th-Pb" && (
            <button onClick={excludeDiscordant}
              className="px-2 py-1 text-[10px] rounded-md bg-amber-50 text-amber-700 hover:bg-amber-100 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />Discordant
            </button>
          )}
        </div>
        <span className="text-[11px] text-secondary-label">
          n = <span className="font-medium text-foreground">{includedCount}</span> spots
          {activeSpots.length !== includedCount && (
            <span className="text-tertiary-label"> ({activeSpots.length} in range)</span>
          )}
        </span>
      </div>

      {/* Spot table */}
      <div className="px-2 pb-1 flex-1 overflow-auto flex-shrink-0 min-h-0" style={{ maxHeight: 220 }}>
        <table className="w-full text-[11px] border-collapse">
          <thead className="sticky top-0 bg-white/90 backdrop-blur-sm z-10">
            <tr>
              <th className="p-1.5 w-[30px]" />
              {visibleFields.map((f) => (
                <th key={f.key} className="p-1.5 text-left font-medium text-tertiary-label" style={{ width: f.width }}>
                  {f.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {concordanceFiltered.map((spot) => {
              const isIncluded = !spot.s_discarded;
              const isHovered = hoveredSpotId === spot.spot_id;
              const inConcRange = spot._inConcRange;
              return (
                <tr
                  key={`${spot.sample_id}-${spot.spot_id}`}
                  ref={(el) => { if (el) tableRowRefs.current.set(spot.spot_id, el); }}
                  className={`border-t border-black/[0.04] transition-all ${
                    isHovered ? "bg-accent/[0.06] ring-1 ring-inset ring-accent/20" : ""
                  } ${!inConcRange ? "opacity-30" : isIncluded ? "hover:bg-black/[0.02]" : "opacity-50"}`}
                >
                  <td className="p-1.5 text-center">
                    <button
                      onClick={() => toggleSpot(spot.spot_id)}
                      className={`w-4 h-4 rounded flex items-center justify-center border transition-all ${
                        isIncluded && inConcRange
                          ? "bg-accent border-accent text-white"
                          : "border-black/15 bg-white"
                      }`}
                    >
                      {isIncluded ? <Check className="w-2.5 h-2.5" /> : <Minus className="w-2.5 h-2.5 text-black/20" />}
                    </button>
                  </td>
                  {visibleFields.map((f) => {
                    const val = getFieldValue(spot as unknown as Record<string, unknown>, f.key);
                    const isDiscordant =
                      f.key === "concordance" && typeof val === "number" &&
                      (val < CONCORDANCE_MIN || val > CONCORDANCE_MAX);
                    return (
                      <td key={f.key}
                        className={`p-1.5 ${
                          !isIncluded ? "line-through text-tertiary-label"
                          : isDiscordant ? "text-red-500 font-medium"
                          : f.calcGroup === "age" ? "text-foreground font-medium"
                          : "text-secondary-label"
                        }`}
                      >
                        {f.format ? f.format(val) : val != null ? String(val) : "—"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Live stats bar */}
      <div className="px-3 pb-2 flex-shrink-0 border-t border-black/[0.04]">
        {allowedMethods.length > 1 && (
          <div className="flex gap-1 pt-2 pb-1.5">
            {allowedMethods.map((m) => (
              <button key={m} onClick={() => setActiveMethod(m)}
                className={`px-2.5 py-1 text-[10px] rounded-full transition-all ${
                  activeMethod === m
                    ? "bg-foreground text-white font-medium"
                    : "bg-grouped-bg text-secondary-label hover:bg-black/5"
                }`}
              >
                {CALC_METHOD_INFO[m].label}
              </button>
            ))}
          </div>
        )}
        <div className="mt-1 p-2.5 rounded-xl bg-grouped-bg">
          <p className="text-[10px] text-tertiary-label mb-1.5">
            {CALC_METHOD_INFO[activeMethod].labelEn} · {CALC_METHOD_INFO[activeMethod].description}
          </p>
          {result.method === "weightedMean" && (
            <div className="flex items-baseline gap-3">
              <span className="text-[16px] font-semibold" style={{ color }}>
                {result.n > 0 ? `${result.mean.toFixed(2)} ± ${result.error.toFixed(2)} Ma` : "—"}
              </span>
              <span className="text-[11px] text-secondary-label">MSWD = {result.mswd.toFixed(2)} · n = {result.n}/{includedCount}</span>
            </div>
          )}
          {result.method === "peakAge" && (
            <div className="flex items-baseline gap-3">
              <span className="text-[16px] font-semibold" style={{ color }}>
                {result.n > 0 ? `${result.peakAge.toFixed(2)} Ma` : "—"}
              </span>
              <span className="text-[11px] text-secondary-label">Peak density = {result.peakDensity.toFixed(4)} · n = {result.n}</span>
            </div>
          )}
          {result.method === "minApparentAge" && (
            <div className="flex items-baseline gap-3">
              <span className="text-[16px] font-semibold" style={{ color }}>
                {result.age > 0 ? `${result.age.toFixed(2)} ± ${result.error.toFixed(2)} Ma` : "—"}
              </span>
              <span className="text-[11px] text-secondary-label">Spot #{result.grainId} · Conc. {result.concordance.toFixed(1)}%</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
