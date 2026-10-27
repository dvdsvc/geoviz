"use client";

import { useMemo } from "react";
import { X } from "lucide-react";
import { Sample } from "@/types";
import { ICS_STAGES, findStage, IcsStage } from "@/utils/ics2023";

interface StratColumnProps {
  sample: Sample;
  onClose: () => void;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

// Period display ranges — show a window around the sample's age
function getColumnRange(ageMa: number | null): { startMa: number; endMa: number } {
  if (ageMa == null) return { startMa: 0, endMa: 360 };
  // Show ±30 Ma around the sample, clamped to 0-360
  return {
    startMa: Math.max(0, ageMa - 30),
    endMa: Math.min(360, ageMa + 30),
  };
}

export default function StratColumn({ sample, onClose }: StratColumnProps) {
  const color = regionColors[sample.region] || "#007aff";

  const { visibleStages, sampleStage, W, PAD, plotW } = useMemo(() => {
    const range = getColumnRange(sample.ageMa);

    // Get stages visible in the column range, sorted old→young
    const visibleStages = ICS_STAGES
      .filter((s) => s.startMa > range.startMa && s.endMa < range.endMa)
      .sort((a, b) => b.startMa - a.startMa);

    const sampleStage = sample.ageMa != null ? findStage(sample.ageMa) : null;

    const W = 320;
    const PAD = { top: 10, bottom: 10, left: 100, right: 20 };
    const plotW = W - PAD.left - PAD.right;

    return { visibleStages, sampleStage, W, PAD, plotW };
  }, [sample]);

  const totalSpan = visibleStages.length > 0
    ? visibleStages[0].startMa - visibleStages[visibleStages.length - 1].endMa
    : 1;

  const H = PAD.top + visibleStages.length * 38 + PAD.bottom;
  const unitH = 38;

  // Map age to x position (older=left, younger=right)
  const ageRange = visibleStages.length > 0
    ? { min: visibleStages[visibleStages.length - 1].endMa, max: visibleStages[0].startMa }
    : { min: 0, max: 1 };

  const ageToX = (age: number) =>
    PAD.left + ((age - ageRange.min) / (ageRange.max - ageRange.min)) * plotW;

  return (
    <div className="ios-card overflow-hidden flex flex-col" style={{ width: 340 }}>
      {/* Header */}
      <div className="px-4 pt-3 pb-2 flex items-center justify-between flex-shrink-0">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label">
            ICS 2023 Standard Stratigraphy
          </span>
          <h3 className="text-[15px] font-semibold text-foreground mt-0.5">
            {sample.sampleId}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10"
        >
          <X className="w-3.5 h-3.5 text-secondary-label" />
        </button>
      </div>

      {/* Sample info */}
      <div className="px-4 pb-2 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
          <span className="text-[12px] text-secondary-label">
            {sample.formation}
            {sample.ageMa != null && (
              <span className="font-medium text-foreground ml-2">
                {sample.ageMa} Ma
              </span>
            )}
          </span>
        </div>
        {sampleStage && (
          <p className="text-[11px] text-secondary-label mt-1 ml-[14px]">
            Stage: <span className="font-medium text-foreground">{sampleStage.name}</span>
            {" "}({sampleStage.period})
          </p>
        )}
      </div>

      {/* SVG Column */}
      <div className="px-3 pb-2 flex-1 overflow-y-auto flex-shrink-0">
        <svg width={W} height={H} className="block">
          {/* Age axis at top */}
          {(() => {
            const ticks: number[] = [];
            const step = 10;
            const start = Math.ceil(ageRange.min / step) * step;
            for (let v = start; v <= ageRange.max; v += step) ticks.push(v);
            return ticks.map((v) => (
              <g key={v}>
                <line
                  x1={ageToX(v)} y1={PAD.top}
                  x2={ageToX(v)} y2={H - PAD.bottom}
                  stroke="rgba(0,0,0,0.04)"
                  strokeWidth={0.5}
                />
                <text
                  x={ageToX(v)}
                  y={PAD.top - 2}
                  textAnchor="middle"
                  style={{ fontSize: 8, fill: "rgba(60,60,67,0.4)", fontFamily: "Inter, sans-serif" }}
                >
                  {v}
                </text>
              </g>
            ));
          })()}

          {/* Stage blocks */}
          {visibleStages.map((stage, i) => {
            const y = PAD.top + i * unitH;
            const x1 = ageToX(stage.startMa);
            const x2 = ageToX(stage.endMa);
            const w = Math.max(x2 - x1, 4);

            const isSampleStage = sampleStage?.name === stage.name;

            return (
              <g key={stage.name}>
                {/* Stage block */}
                <rect
                  x={Math.min(x1, x2)}
                  y={y + 2}
                  width={w}
                  height={unitH - 4}
                  fill={stage.color}
                  opacity={isSampleStage ? 0.9 : 0.35}
                  rx={3}
                  stroke={isSampleStage ? color : "rgba(0,0,0,0.06)"}
                  strokeWidth={isSampleStage ? 2 : 0.5}
                />

                {/* Stage name (left) */}
                <text
                  x={PAD.left - 6}
                  y={y + unitH / 2 + 3}
                  textAnchor="end"
                  style={{
                    fontSize: 9,
                    fontWeight: isSampleStage ? 700 : 400,
                    fill: isSampleStage ? "#1c1c1e" : "rgba(60,60,67,0.55)",
                    fontFamily: "Inter, sans-serif",
                  }}
                >
                  {stage.name}
                </text>

                {/* Period label inside block if wide enough */}
                {w > 50 && (
                  <text
                    x={Math.min(x1, x2) + w / 2}
                    y={y + unitH / 2 + 3}
                    textAnchor="middle"
                    style={{
                      fontSize: 8,
                      fill: isSampleStage ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.5)",
                      fontFamily: "Inter, sans-serif",
                    }}
                  >
                    {stage.period}
                  </text>
                )}

                {/* Age boundary labels */}
                <text
                  x={ageToX(stage.startMa)}
                  y={y + unitH - 4}
                  textAnchor="middle"
                  style={{ fontSize: 7, fill: "rgba(60,60,67,0.3)", fontFamily: "Inter, sans-serif" }}
                >
                  {stage.startMa.toFixed(1)}
                </text>

                {/* Sample marker */}
                {isSampleStage && sample.ageMa != null && (
                  <g>
                    <line
                      x1={ageToX(sample.ageMa)}
                      y1={y + 2}
                      x2={ageToX(sample.ageMa)}
                      y2={y + unitH - 2}
                      stroke={color}
                      strokeWidth={2.5}
                      strokeLinecap="round"
                    />
                    <circle
                      cx={ageToX(sample.ageMa)}
                      cy={y + unitH / 2}
                      r={5}
                      fill={color}
                      stroke="white"
                      strokeWidth={2}
                    />
                    <text
                      x={ageToX(sample.ageMa)}
                      y={y - 1}
                      textAnchor="middle"
                      style={{
                        fontSize: 9,
                        fontWeight: 700,
                        fill: color,
                        fontFamily: "Inter, sans-serif",
                      }}
                    >
                      {sample.sampleId} ({sample.ageMa} Ma)
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="px-4 pb-3 flex-shrink-0">
        <p className="text-[10px] text-tertiary-label">
          Based on ICS International Chronostratigraphic Chart 2023
        </p>
      </div>
    </div>
  );
}
