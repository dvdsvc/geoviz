"use client";

import { Sample } from "@/types";
import { X, MapPin, Clock, BookOpen, ScatterChart, BarChart3, Layers, Database } from "lucide-react";

interface SampleDetailProps {
  sample: Sample;
  onClose: () => void;
  onConcordia?: () => void;
  onWeightedMean?: () => void;
  onStratColumn?: () => void;
  onSpots?: () => void;
  onViewInSource?: () => void;
  hasSource?: boolean;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

function InfoRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="ios-section-item flex justify-between items-baseline">
      <span className="text-[13px] text-secondary-label">{label}</span>
      <span className="text-[15px] text-foreground text-right max-w-[60%]">{value}</span>
    </div>
  );
}

export default function SampleDetail({ sample: s, onClose, onConcordia, onWeightedMean, onStratColumn, onSpots, onViewInSource, hasSource }: SampleDetailProps) {
  // Build compact geography line: Region · Location · City · SpecificLocation · Basin
  const geoParts = [s.regionProvince, s.location, s.city, s.specificLocation, s.basin].filter(Boolean);
  const geoLine = geoParts.join(" · ");

  // Build stratigraphy line: Group / Formation / Member_Depth
  const stratParts = [
    s.group && `${s.group}`,
    s.formation && `${s.formation}`,
    s.memberDepth && `${s.memberDepth}`,
  ].filter(Boolean);
  const stratLine = stratParts.join(" / ");

  // Analysis fields list
  const analysisFields: [string, string | number | null | undefined][] = [
    ["Rock Type", s.rockType],
    ["Mineral", s.datingMineral],
    ["System", s.datingSystem],
    ["Technique", s.technique],
    ["Age Type", s.ageType],
    ["Physical Method", s.physicalMethod],
    ["Distribution", s.distributionState],
    ["N Grains", s.nGrains],
  ];

  return (
    <div className="ios-card overflow-hidden max-h-[calc(100vh-120px)] overflow-y-auto">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ background: regionColors[s.region] }}
            />
            <span className="text-[13px] text-secondary-label">{s.region}</span>
          </div>
          <h3 className="text-[20px] font-semibold text-foreground mt-0.5 tracking-tight">{s.sampleId}</h3>
        </div>
        <button
          onClick={onClose}
          className="w-7 h-7 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10 transition-colors"
        >
          <X className="w-3.5 h-3.5 text-secondary-label" />
        </button>
      </div>

      {/* Geography & Stratigraphy — compact block */}
      {(geoLine || stratLine || s.gps) && (
        <div className="mx-4 mb-3 px-4 py-2.5 rounded-xl bg-grouped-bg">
          <div className="flex items-start gap-2">
            <MapPin className="w-3.5 h-3.5 text-tertiary-label mt-0.5 flex-shrink-0" />
            <div className="min-w-0">
              {geoLine && (
                <p className="text-[13px] text-foreground leading-relaxed">{geoLine}</p>
              )}
              {stratLine && (
                <p className="text-[12px] text-secondary-label mt-0.5">{stratLine}</p>
              )}
              {s.gps && (
                <p className="text-[10px] text-tertiary-label mt-0.5 font-mono">{s.gps}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Age highlight card */}
      {s.ageMa && (
        <div className="mx-4 mb-3 px-4 py-3 rounded-xl flex items-center gap-3"
          style={{ background: regionColors[s.region] + "0D" }}>
          <Clock className="w-4 h-4 flex-shrink-0" style={{ color: regionColors[s.region] }} />
          <div>
            <span className="text-[22px] font-bold tracking-tight" style={{ color: regionColors[s.region] }}>
              {s.ageMa}
            </span>
            <span className="text-[14px] font-medium ml-1" style={{ color: regionColors[s.region] }}>Ma</span>
            {s.error && (
              <span className="text-[13px] text-secondary-label ml-1">± {s.error} (1σ)</span>
            )}
          </div>
          {s.mswd != null && (
            <span className="ml-auto text-[12px] text-tertiary-label">MSWD {s.mswd}</span>
          )}
        </div>
      )}

      {/* Analysis section */}
      <div className="mx-4 mb-3">
        <h4 className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label px-4 mb-1.5">
          Analysis
        </h4>
        <div className="ios-section">
          {analysisFields.map(([label, value]) => (
            <InfoRow key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      {/* Reference */}
      {s.reference && (
        <div className="mx-4 mb-4">
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label px-4 mb-1.5">
            Reference
          </h4>
          <div className="ios-section">
            <div className="ios-section-item">
              <p className="text-[14px] text-foreground leading-relaxed">{s.reference}</p>
            </div>
          </div>
        </div>
      )}

      {s.remarks && (
        <p className="mx-4 mb-3 text-[12px] text-tertiary-label italic px-4">{s.remarks}</p>
      )}

      {/* Action buttons */}
      <div className="mx-4 mb-4 space-y-2">
        {hasSource && onViewInSource && (
          <button
            onClick={onViewInSource}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl
              bg-accent-light text-accent text-[13px] font-medium
              hover:bg-accent/10 transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5" />
            View in Source
          </button>
        )}

        {/* Chart buttons row */}
        <div className="flex gap-2">
          {onConcordia && (
            <button
              onClick={onConcordia}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl
                bg-violet-50 text-violet-600 text-[12px] font-medium
                hover:bg-violet-100 transition-colors"
            >
              <ScatterChart className="w-3.5 h-3.5" />
              Concordia
            </button>
          )}
          {onWeightedMean && s.ageMa != null && (
            <button
              onClick={onWeightedMean}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl
                bg-emerald-50 text-emerald-700 text-[12px] font-medium
                hover:bg-emerald-100 transition-colors"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              Wtd. Mean
            </button>
          )}
          {onStratColumn && (
            <button
              onClick={onStratColumn}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl
                bg-amber-50 text-amber-700 text-[12px] font-medium
                hover:bg-amber-100 transition-colors"
            >
              <Layers className="w-3.5 h-3.5" />
              Strat
            </button>
          )}
          {onSpots && (
            <button
              onClick={onSpots}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl
                bg-sky-50 text-sky-700 text-[12px] font-medium
                hover:bg-sky-100 transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              Spots
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
