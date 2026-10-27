"use client";

import { useMemo } from "react";
import { X } from "lucide-react";
import { Sample } from "@/types";
import { SpotRecord, weightedMean } from "@/utils/spotCalc";

interface WeightedMeanPlotProps {
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

export default function WeightedMeanPlot({ sample, spots, onClose }: WeightedMeanPlotProps) {
  const color = regionColors[sample.region] || "#007aff";

  // Filter spots for calculation (remove discarded)
  const validSpots = useMemo(
    () => spots.filter((s) => !s.s_discarded),
    [spots]
  );

  // Calculate weighted mean
  const wm = useMemo(() => weightedMean(validSpots), [validSpots]);

  // Prepare data for plotting
  const { grains, ageDomain, W, H, PAD, plotW, plotH } = useMemo(() => {
    const grains = validSpots
      .filter((s) => s.age_206_238_val != null && s.age_206_238_err != null)
      .map((s) => ({
        id: s.spot_id,
        age: s.age_206_238_val!,
        error: s.age_206_238_err!,
        concordance: s.concordance ?? 0,
      }));

    if (grains.length === 0) {
      return {
        grains: [],
        ageDomain: [0, 100] as [number, number],
        W: 300,
        H: 220,
        PAD: { top: 10, right: 14, bottom: 30, left: 40 },
        plotW: 246,
        plotH: 180,
      };
    }

    const allMin = Math.min(...grains.map((g) => g.age - g.error * 2));
    const allMax = Math.max(...grains.map((g) => g.age + g.error * 2));
    const pad = (allMax - allMin) * 0.15 || 5;

    const W = 300;
    const H = 220;
    const PAD = { top: 10, right: 14, bottom: 30, left: 40 };
    const plotW = W - PAD.left - PAD.right;
    const plotH = H - PAD.top - PAD.bottom;

    return {
      grains,
      ageDomain: [allMin - pad, allMax + pad] as [number, number],
      W,
      H,
      PAD,
      plotW,
      plotH,
    };
  }, [validSpots]);

  const scaleX = (age: number) =>
    PAD.left + ((age - ageDomain[0]) / (ageDomain[1] - ageDomain[0])) * plotW;

  const grainSpacing = plotH / (grains.length + 1);

  return (
    <div className="ios-card overflow-hidden flex flex-col" style={{ width: 340 }}>
      <div className="px-4 pt-3 pb-2 flex items-center justify-between flex-shrink-0">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label">
            Weighted Mean Age
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

      <div className="px-3 pb-1 flex-shrink-0">
        <svg width={W} height={H} className="block">
          <line
            x1={scaleX(wm.mean)}
            y1={PAD.top}
            x2={scaleX(wm.mean)}
            y2={PAD.top + plotH}
            stroke={color}
            strokeWidth={2}
            strokeDasharray="4,3"
            opacity={0.7}
          />

          <rect
            x={scaleX(wm.mean - wm.error * 2)}
            y={PAD.top}
            width={scaleX(wm.mean + wm.error * 2) - scaleX(wm.mean - wm.error * 2)}
            height={plotH}
            fill={color}
            opacity={0.06}
          />

          {grains.map((g, i) => {
            const y = PAD.top + (i + 1) * grainSpacing;
            const concColor =
              g.concordance >= 95 && g.concordance <= 105
                ? color
                : g.concordance >= 90 && g.concordance <= 110
                ? "#e9c46a"
                : "#e63946";

            return (
              <g key={g.id}>
                <line
                  x1={scaleX(g.age - g.error * 2)}
                  y1={y}
                  x2={scaleX(g.age + g.error * 2)}
                  y2={y}
                  stroke={concColor}
                  strokeWidth={1}
                  opacity={0.4}
                />
                <line
                  x1={scaleX(g.age - g.error * 2)}
                  y1={y - 3}
                  x2={scaleX(g.age - g.error * 2)}
                  y2={y + 3}
                  stroke={concColor}
                  strokeWidth={1}
                  opacity={0.4}
                />
                <line
                  x1={scaleX(g.age + g.error * 2)}
                  y1={y - 3}
                  x2={scaleX(g.age + g.error * 2)}
                  y2={y + 3}
                  stroke={concColor}
                  strokeWidth={1}
                  opacity={0.4}
                />
                <circle
                  cx={scaleX(g.age)}
                  cy={y}
                  r={3.5}
                  fill={concColor}
                  stroke="white"
                  strokeWidth={1}
                />
                <text
                  x={PAD.left - 4}
                  y={y + 3}
                  textAnchor="end"
                  style={{ fontSize: 8, fill: "rgba(60,60,67,0.4)", fontFamily: "Inter, sans-serif" }}
                >
                  {i + 1}
                </text>
              </g>
            );
          })}

          <line
            x1={PAD.left}
            y1={PAD.top + plotH}
            x2={PAD.left + plotW}
            y2={PAD.top + plotH}
            stroke="rgba(0,0,0,0.12)"
            strokeWidth={1}
          />

          {(() => {
            const ticks: number[] = [];
            const step = Math.pow(10, Math.floor(Math.log10(ageDomain[1] - ageDomain[0]))) / 2;
            const start = Math.ceil(ageDomain[0] / step) * step;
            for (let v = start; v <= ageDomain[1]; v += step) {
              ticks.push(v);
            }
            return ticks.map((v) => (
              <g key={v}>
                <line
                  x1={scaleX(v)}
                  y1={PAD.top + plotH}
                  x2={scaleX(v)}
                  y2={PAD.top + plotH + 4}
                  stroke="rgba(0,0,0,0.2)"
                  strokeWidth={1}
                />
                <text
                  x={scaleX(v)}
                  y={PAD.top + plotH + 16}
                  textAnchor="middle"
                  style={{ fontSize: 9, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}
                >
                  {v.toFixed(v % 1 === 0 ? 0 : 1)}
                </text>
              </g>
            ));
          })()}

          <text
            x={PAD.left + plotW / 2}
            y={H - 4}
            textAnchor="middle"
            style={{ fontSize: 10, fill: "rgba(60,60,67,0.5)", fontFamily: "Inter, sans-serif" }}
          >
            Age (Ma)
          </text>
        </svg>
      </div>

      <div className="px-4 pb-3 flex-shrink-0">
        <div className="flex items-center gap-3 text-[12px]">
          <span className="text-foreground font-semibold">{wm.mean.toFixed(2)} ± {wm.error.toFixed(2)} Ma</span>
          <span className="text-tertiary-label">MSWD = {wm.mswd.toFixed(2)}</span>
          <span className="text-tertiary-label">n = {wm.n}</span>
        </div>
        <p className="text-[10px] text-tertiary-label mt-1">
          <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: color }} /> Concordant
          <span className="inline-block w-2 h-2 rounded-full mr-1 ml-3" style={{ background: "#e9c46a" }} /> Slightly discordant
          <span className="inline-block w-2 h-2 rounded-full mr-1 ml-3" style={{ background: "#e63946" }} /> Discordant
        </p>
      </div>
    </div>
  );
}
