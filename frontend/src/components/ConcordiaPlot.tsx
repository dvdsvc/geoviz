"use client";

import { useMemo } from "react";
import { X } from "lucide-react";
import { Sample } from "@/types";
import { SpotRecord } from "@/utils/spotCalc";
import { concordiaPoint, concordiaCurve } from "@/utils/concordia";

interface ConcordiaPlotProps {
  sample: Sample;
  spots: SpotRecord[];
  onClose: () => void;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

export default function ConcordiaPlot({ sample, spots, onClose }: ConcordiaPlotProps) {
  const color = regionColors[sample.region] || "#007aff";

  const { curve, plotGrains, meanPoint, xDomain, yDomain } = useMemo(() => {
    const curve = concordiaCurve(400, 1);

    const mappedGrains = spots
      .filter((s) => !s.s_discarded && s.r206_238_val != null && s.r207_235_val != null)
      .map((s) => ({
        x: s.r206_238_val!,
        y: s.r207_235_val!,
        concordance: s.concordance ?? 0,
        age: s.age_206_238_val ?? 0,
        spotId: s.spot_id,
      }));

    const ageMa = sample.ageMa ?? 150;
    const meanPoint = concordiaPoint(ageMa);

    const allX = [...curve.map((p) => p.x), ...mappedGrains.map((g) => g.x), meanPoint.x];
    const allY = [...curve.map((p) => p.y), ...mappedGrains.map((g) => g.y), meanPoint.y];
    const xMin = Math.min(...allX) * 0.92;
    const xMax = Math.max(...allX) * 1.08;
    const yMin = Math.min(...allY) * 0.92;
    const yMax = Math.max(...allY) * 1.08;

    return {
      curve,
      plotGrains: mappedGrains,
      meanPoint,
      xDomain: [xMin, xMax] as [number, number],
      yDomain: [yMin, yMax] as [number, number],
    };
  }, [sample, spots]);

  const W = 300;
  const H = 260;
  const PAD = { top: 12, right: 12, bottom: 36, left: 44 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const scaleX = (v: number) => PAD.left + (v - xDomain[0]) / (xDomain[1] - xDomain[0]) * plotW;
  const scaleY = (v: number) => PAD.top + plotH - (v - yDomain[0]) / (yDomain[1] - yDomain[0]) * plotH;

  const curvePath = curve
    .map((p, i) => `${i === 0 ? "M" : "L"}${scaleX(p.x).toFixed(2)},${scaleY(p.y).toFixed(2)}`)
    .join(" ");

  const labelAges = [50, 100, 150, 200, 250, 300, 350];

  return (
    <div className="ios-card overflow-hidden flex flex-col" style={{ width: 340 }}>
      <div className="px-4 pt-3 pb-2 flex items-center justify-between flex-shrink-0">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label">
            U-Pb Concordia
          </span>
          <h3 className="text-[16px] font-semibold text-foreground mt-0.5">{sample.sampleId}</h3>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10"
        >
          <X className="w-3.5 h-3.5 text-secondary-label" />
        </button>
      </div>

      <div className="px-4 pb-2 flex items-center gap-2 flex-shrink-0">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
        <span className="text-[12px] text-secondary-label">
          {sample.ageMa != null ? `${sample.ageMa} Ma` : "No age"}
          {sample.error ? ` ± ${sample.error}` : ""}
          {sample.mswd != null ? `  MSWD ${sample.mswd}` : ""}
        </span>
      </div>

      <div className="px-3 pb-2 flex-shrink-0">
        <svg width={W} height={H} className="block">
          {Array.from({ length: 6 }, (_, i) => {
            const v = xDomain[0] + (i / 5) * (xDomain[1] - xDomain[0]);
            return (
              <line key={`gx-${i}`} x1={scaleX(v)} y1={PAD.top} x2={scaleX(v)} y2={PAD.top + plotH}
                stroke="rgba(0,0,0,0.04)" strokeWidth={0.5} />
            );
          })}
          {Array.from({ length: 6 }, (_, i) => {
            const v = yDomain[0] + (i / 5) * (yDomain[1] - yDomain[0]);
            return (
              <line key={`gy-${i}`} x1={PAD.left} y1={scaleY(v)} x2={PAD.left + plotW} y2={scaleY(v)}
                stroke="rgba(0,0,0,0.04)" strokeWidth={0.5} />
            );
          })}

          <path d={curvePath} fill="none" stroke="#1c1c1e" strokeWidth={1.5} opacity={0.25} />

          {labelAges.map((age) => {
            const pt = concordiaPoint(age);
            const x = scaleX(pt.x);
            const y = scaleY(pt.y);
            if (x < PAD.left || x > PAD.left + plotW || y < PAD.top || y > PAD.top + plotH) return null;
            return (
              <text
                key={age}
                x={x + 4}
                y={y - 4}
                style={{ fontSize: 8, fill: "rgba(60,60,67,0.35)", fontFamily: "Inter, sans-serif" }}
              >
                {age}
              </text>
            );
          })}

          {plotGrains.map((g, i) => {
            const concColor =
              g.concordance >= 95 && g.concordance <= 105
                ? color
                : g.concordance >= 90 && g.concordance <= 110
                ? "#e9c46a"
                : "#e63946";
            return (
              <circle
                key={i}
                cx={scaleX(g.x)}
                cy={scaleY(g.y)}
                r={3.5}
                fill={concColor}
                opacity={0.7}
                stroke="white"
                strokeWidth={0.6}
              >
                <title>{g.spotId}: {g.age.toFixed(1)} Ma, {g.concordance.toFixed(0)}% concordant</title>
              </circle>
            );
          })}

          <circle
            cx={scaleX(meanPoint.x)}
            cy={scaleY(meanPoint.y)}
            r={5.5}
            fill={color}
            stroke="white"
            strokeWidth={2}
          />

          <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + plotH}
            stroke="rgba(0,0,0,0.12)" strokeWidth={1} />
          <line x1={PAD.left} y1={PAD.top + plotH} x2={PAD.left + plotW} y2={PAD.top + plotH}
            stroke="rgba(0,0,0,0.12)" strokeWidth={1} />

          {Array.from({ length: 6 }, (_, i) => {
            const v = xDomain[0] + (i / 5) * (xDomain[1] - xDomain[0]);
            return (
              <text key={`tx-${i}`} x={scaleX(v)} y={PAD.top + plotH + 14} textAnchor="middle"
                style={{ fontSize: 9, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>{v.toFixed(3)}</text>
            );
          })}

          {Array.from({ length: 6 }, (_, i) => {
            const v = yDomain[0] + (i / 5) * (yDomain[1] - yDomain[0]);
            return (
              <text key={`ty-${i}`} x={PAD.left - 6} y={scaleY(v) + 3} textAnchor="end"
                style={{ fontSize: 9, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>{v.toFixed(2)}</text>
            );
          })}

          <text x={PAD.left + plotW / 2} y={H - 4} textAnchor="middle"
            style={{ fontSize: 10, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>
            ²⁰⁶Pb/²³⁸U
          </text>
          <text x={12} y={PAD.top + plotH / 2} textAnchor="middle"
            transform={`rotate(-90, 12, ${PAD.top + plotH / 2})`}
            style={{ fontSize: 10, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}>
            ²⁰⁷Pb/²³⁵U
          </text>
        </svg>
      </div>

      <div className="px-4 pb-3 flex-shrink-0">
        <p className="text-[10px] text-tertiary-label leading-snug">
          n={plotGrains.length} spots · Hover dots for details
        </p>
        <p className="text-[10px] text-tertiary-label mt-1">
          <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: color }} /> Concordant
          <span className="inline-block w-2 h-2 rounded-full mr-1 ml-3" style={{ background: "#e9c46a" }} /> 90-110%
          <span className="inline-block w-2 h-2 rounded-full mr-1 ml-3" style={{ background: "#e63946" }} /> &lt;90%
        </p>
      </div>
    </div>
  );
}
