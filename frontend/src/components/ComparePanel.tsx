"use client";

import { useMemo } from "react";
import { X, GitCompareArrows } from "lucide-react";
import { Sample } from "@/types";

interface ComparePanelProps {
  samples: Sample[];
  onClose: () => void;
  onRemove: (id: string) => void;
}

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

interface FieldDef {
  key: keyof Sample | "ageDisplay";
  label: string;
  format?: (s: Sample) => string;
}

const FIELDS: FieldDef[] = [
  { key: "region", label: "Region" },
  { key: "basin", label: "Basin" },
  { key: "formation", label: "Formation" },
  { key: "group", label: "Group" },
  { key: "location", label: "Location" },
  {
    key: "ageDisplay",
    label: "Age (Ma)",
    format: (s) =>
      s.ageMa != null
        ? `${s.ageMa}${s.error != null ? ` ± ${s.error}` : ""}`
        : "—",
  },
  { key: "mswd", label: "MSWD", format: (s) => s.mswd != null ? String(s.mswd) : "—" },
  { key: "nGrains", label: "N Grains", format: (s) => s.nGrains != null ? String(s.nGrains) : "—" },
  { key: "rockType", label: "Rock Type" },
  { key: "datingMineral", label: "Mineral" },
  { key: "datingSystem", label: "System" },
  { key: "technique", label: "Technique" },
  { key: "ageType", label: "Age Type" },
  { key: "memberDepth", label: "Member / Depth" },
  { key: "reference", label: "Reference" },
];

function fieldValue(s: Sample, f: FieldDef): string {
  if (f.format) return f.format(s);
  const v = s[f.key as keyof Sample];
  return v != null && v !== "" ? String(v) : "—";
}

export default function ComparePanel({ samples, onClose, onRemove }: ComparePanelProps) {
  // Detect which fields have differences across samples
  const diffFields = useMemo(() => {
    const diffs = new Set<string>();
    for (const f of FIELDS) {
      const vals = samples.map((s) => fieldValue(s, f));
      if (new Set(vals).size > 1) diffs.add(f.key);
    }
    return diffs;
  }, [samples]);

  const colW = samples.length <= 2 ? 140 : samples.length <= 3 ? 120 : 100;

  return (
    <div className="ios-card overflow-hidden flex flex-col" style={{ width: 120 + colW * samples.length + 16 }}>
      {/* Header */}
      <div className="px-4 pt-3 pb-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <GitCompareArrows className="w-4 h-4 text-accent" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-tertiary-label">
            Compare Samples
          </span>
          <span className="text-[11px] text-tertiary-label">({samples.length})</span>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10"
        >
          <X className="w-3.5 h-3.5 text-secondary-label" />
        </button>
      </div>

      {/* Table */}
      <div className="px-2 pb-3 flex-1 overflow-auto flex-shrink-0">
        <table className="w-full text-[12px] border-collapse">
          {/* Column headers — sample IDs */}
          <thead>
            <tr>
              <th className="text-left p-2 text-tertiary-label font-medium w-[110px] sticky left-0 bg-white/80 backdrop-blur-sm" />
              {samples.map((s) => (
                <th key={s.id} className="p-2 text-center font-semibold" style={{ width: colW }}>
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: regionColors[s.region] || "#666" }}
                      />
                      <span className="text-foreground">{s.sampleId}</span>
                      <button
                        onClick={() => onRemove(s.id)}
                        className="w-4 h-4 rounded-full bg-black/5 flex items-center justify-center hover:bg-red-500/20 hover:text-red-500 transition-colors"
                        title="Remove from comparison"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                    {s.ageMa != null && (
                      <span className="text-accent font-medium">{s.ageMa} Ma</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Rows */}
          <tbody>
            {FIELDS.map((f) => {
              const isDiff = diffFields.has(f.key);
              return (
                <tr
                  key={f.key}
                  className={isDiff ? "bg-amber-50/60" : "hover:bg-black/[0.02]"}
                >
                  <td className="p-2 text-tertiary-label font-medium text-[11px] sticky left-0 bg-inherit">
                    {f.label}
                  </td>
                  {samples.map((s) => (
                    <td
                      key={s.id}
                      className={`p-2 text-center ${
                        isDiff ? "text-foreground font-medium" : "text-secondary-label"
                      }`}
                    >
                      {fieldValue(s, f)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer hint */}
      <div className="px-4 pb-3 flex-shrink-0">
        <p className="text-[10px] text-tertiary-label">
          <span className="inline-block w-3 h-3 rounded mr-1 bg-amber-50 border border-amber-200 align-middle" />
          Highlighted rows indicate differences between samples. Cmd/Ctrl+Click in sidebar to add up to 4 samples.
        </p>
      </div>
    </div>
  );
}
