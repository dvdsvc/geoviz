"use client";

import { useRef, useEffect, useMemo, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sample } from "@/types";
import { GEO_PERIODS, ageToX } from "@/utils/timeline";

interface TimelineDrawerProps {
  samples: Sample[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  open: boolean;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

const MIN_MA = 0;
const MAX_MA = 350;

export default function TimelineDrawer({ samples, selectedId, onSelect, open }: TimelineDrawerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgContainerRef = useRef<HTMLDivElement>(null);
  const [containerW, setContainerW] = useState(900);

  // Viewport state: scaleX and panX (in data-space units)
  const [scaleX, setScaleX] = useState(1);
  const [panX, setPanX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ x: number; panX: number } | null>(null);

  const PAD = { left: 40, right: 20, top: 8, bottom: 28 };
  const H = 160;

  const withAge = useMemo(
    () => samples.filter((s) => s.ageMa != null) as Array<Sample & { ageMa: number }>,
    [samples]
  );

  // Measure container width
  useEffect(() => {
    const el = svgContainerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerW(entry.contentRect.width);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const plotW = Math.max(containerW - PAD.left - PAD.right, 200);

  // Data-space to SVG x
  const baseToX = useCallback(
    (ageMa: number) => PAD.left + ageToX(ageMa, plotW, MIN_MA, MAX_MA),
    [plotW]
  );

  const toX = useCallback(
    (ageMa: number) => {
      const base = baseToX(ageMa);
      // Apply pan and scale around center
      const center = PAD.left + plotW / 2;
      return center + (base - center - panX) * scaleX;
    },
    [baseToX, plotW, panX, scaleX]
  );

  // Visible range (data-space)
  const visibleMin = useMemo(() => {
    const center = PAD.left + plotW / 2;
    const leftEdgeX = PAD.left;
    const raw = center + (leftEdgeX - center - panX) * scaleX;
    const age = MIN_MA + ((raw - PAD.left) / plotW) * (MAX_MA - MIN_MA);
    return Math.max(MIN_MA, Math.min(MAX_MA, age));
  }, [plotW, panX, scaleX]);

  const visibleMax = useMemo(() => {
    const center = PAD.left + plotW / 2;
    const rightEdgeX = PAD.left + plotW;
    const raw = center + (rightEdgeX - center - panX) * scaleX;
    const age = MIN_MA + ((raw - PAD.left) / plotW) * (MAX_MA - MIN_MA);
    return Math.max(MIN_MA, Math.min(MAX_MA, age));
  }, [plotW, panX, scaleX]);

  // Wheel zoom
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY;
      const factor = delta > 0 ? 0.9 : 1.1;
      setScaleX((prev) => Math.max(1, Math.min(10, prev * factor)));
    },
    []
  );

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX, panX };
  }, [panX]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging || !dragStartRef.current) return;
      const dx = e.clientX - dragStartRef.current.x;
      setPanX(dragStartRef.current.panX - dx / scaleX);
    },
    [isDragging, scaleX]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    dragStartRef.current = null;
  }, []);

  // Reset view
  const handleReset = useCallback(() => {
    setScaleX(1);
    setPanX(0);
  }, []);

  // Dot layout: compute y-position to avoid overlap
  const dots = useMemo(() => {
    const sorted = [...withAge].sort((a, b) => a.ageMa - b.ageMa);
    const rows: Array<Array<Sample & { ageMa: number }>> = [];

    for (const s of sorted) {
      let placed = false;
      for (const row of rows) {
        const last = row[row.length - 1];
        const lastX = toX(last.ageMa);
        const currX = toX(s.ageMa);
        if (currX - lastX > 50) {
          row.push(s);
          placed = true;
          break;
        }
      }
      if (!placed) {
        rows.push([s]);
      }
    }

    const bandH = 22;
    const dotBaseY = PAD.top + bandH + 20;
    const rowGap = 18;

    const result: Array<{
      s: Sample & { ageMa: number };
      x: number;
      y: number;
      row: number;
      isSelected: boolean;
    }> = [];

    rows.forEach((row, ri) => {
      row.forEach((s) => {
        result.push({
          s,
          x: toX(s.ageMa),
          y: dotBaseY + ri * rowGap,
          row: ri,
          isSelected: s.id === selectedId,
        });
      });
    });

    return result;
  }, [withAge, toX, selectedId]);

  // Tick marks
  const tickInterval = useMemo(() => {
    if (scaleX >= 5) return 10;
    if (scaleX >= 2) return 25;
    return 50;
  }, [scaleX]);

  const ticks = useMemo(() => {
    const arr: number[] = [];
    const start = Math.ceil(visibleMax / tickInterval) * tickInterval;
    const end = Math.floor(visibleMin / tickInterval) * tickInterval;
    for (let v = start; v >= end; v -= tickInterval) {
      if (v >= MIN_MA && v <= MAX_MA) arr.push(v);
    }
    return arr;
  }, [visibleMin, visibleMax, tickInterval]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ y: 180, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 180, opacity: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 35 }}
          className="absolute bottom-0 left-0 right-0 z-[1002]"
          ref={containerRef}
        >
          <div className="ios-card mx-3 mb-3 overflow-hidden select-none">
            {/* Handle bar */}
            <div className="flex justify-center pt-2 pb-1">
              <div className="timeline-handle" />
            </div>

            {/* Header */}
            <div className="px-4 pb-1 flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label">
                Geological Timeline
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-tertiary-label">
                  {withAge.length} samples
                </span>
                <span className="text-[10px] text-tertiary-label">
                  {visibleMax.toFixed(0)}–{visibleMin.toFixed(0)} Ma
                </span>
                <button
                  onClick={handleReset}
                  className="text-[10px] px-2 py-0.5 rounded-md bg-grouped-bg text-secondary-label hover:bg-black/5 transition-colors"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* SVG Timeline */}
            <div
              ref={svgContainerRef}
              className="px-3 pb-3 overflow-hidden cursor-grab active:cursor-grabbing"
              onWheel={handleWheel}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              <svg
                width="100%"
                height={H}
                viewBox={`0 0 ${containerW} ${H}`}
                className="block"
                preserveAspectRatio="none"
              >
                {/* Period color bands */}
                {GEO_PERIODS.map((p) => {
                  const x1 = toX(p.startMa);
                  const x2 = toX(p.endMa);
                  const w = x2 - x1;
                  if (w < 2) return null;
                  return (
                    <g key={p.abbr}>
                      <rect
                        x={x1}
                        y={PAD.top}
                        width={w}
                        height={16}
                        fill={p.color}
                        opacity={0.2}
                        rx={3}
                      />
                      {w > 30 && (
                        <text
                          x={(x1 + x2) / 2}
                          y={PAD.top + 11}
                          textAnchor="middle"
                          style={{ fontSize: 9, fontWeight: 600, fill: p.color }}
                        >
                          {p.abbr}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Tick marks */}
                {ticks.map((age) => {
                  const x = toX(age);
                  if (x < PAD.left - 5 || x > PAD.left + plotW + 5) return null;
                  return (
                    <g key={age}>
                      <line
                        x1={x}
                        y1={PAD.top + 18}
                        x2={x}
                        y2={H - PAD.bottom}
                        stroke="rgba(0,0,0,0.06)"
                        strokeWidth={0.5}
                        strokeDasharray="3,3"
                      />
                      <text
                        x={x}
                        y={H - 8}
                        textAnchor="middle"
                        style={{ fontSize: 9, fill: "rgba(60,60,67,0.4)", fontFamily: "Inter, sans-serif" }}
                      >
                        {age}
                      </text>
                    </g>
                  );
                })}

                {/* "Ma" label */}
                <text
                  x={PAD.left + plotW + 10}
                  y={H - 8}
                  style={{ fontSize: 8, fill: "rgba(60,60,67,0.3)", fontFamily: "Inter, sans-serif" }}
                >
                  Ma
                </text>

                {/* Sample dots */}
                {dots.map(({ s, x, y, isSelected }) => {
                  const color = regionColors[s.region] || "#666";
                  return (
                    <g
                      key={s.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(s.id);
                      }}
                      className="cursor-pointer"
                      role="button"
                      tabIndex={0}
                    >
                      {/* Pulsing ring for selected */}
                      {isSelected && (
                        <circle
                          cx={x}
                          cy={y}
                          r={10}
                          fill="none"
                          stroke={color}
                          strokeWidth={1.5}
                          opacity={0.3}
                        >
                          <animate
                            attributeName="r"
                            values="8;13;8"
                            dur="2s"
                            repeatCount="indefinite"
                          />
                          <animate
                            attributeName="opacity"
                            values="0.4;0;0.4"
                            dur="2s"
                            repeatCount="indefinite"
                          />
                        </circle>
                      )}
                      <circle
                        cx={x}
                        cy={y}
                        r={isSelected ? 5.5 : 4}
                        fill={color}
                        stroke={isSelected ? "#1c1c1e" : "rgba(255,255,255,0.8)"}
                        strokeWidth={isSelected ? 2 : 1}
                      />
                      {/* Label only for selected or non-overlapping */}
                      <text
                        x={x}
                        y={y + (isSelected ? 16 : 14)}
                        textAnchor="middle"
                        style={{
                          fontSize: isSelected ? 9 : 8,
                          fontWeight: isSelected ? 600 : 400,
                          fill: isSelected ? "#1c1c1e" : "rgba(60,60,67,0.5)",
                          fontFamily: "Inter, sans-serif",
                        }}
                      >
                        {s.sampleId}
                      </text>
                    </g>
                  );
                })}

                {/* No-age samples indicator */}
                {samples.filter((s) => s.ageMa == null).length > 0 && (
                  <text
                    x={PAD.left}
                    y={H - 4}
                    style={{ fontSize: 8, fill: "rgba(60,60,67,0.3)", fontFamily: "Inter, sans-serif" }}
                  >
                    {samples.filter((s) => s.ageMa == null).length} samples without age data not shown
                  </text>
                )}
              </svg>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
