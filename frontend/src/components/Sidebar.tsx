"use client";

import { useState, useMemo } from "react";
import { Sample } from "@/types";
import { Search, MapPin, Clock, Layers, PanelLeftClose, PanelLeftOpen, BookOpen, ChevronDown, ChevronRight, SlidersHorizontal } from "lucide-react";
import { clusterSamples, ReferenceGroup } from "@/utils/clusterSamples";

interface SidebarProps {
  samples: Sample[];
  selectedIds: string[];
  onSelect: (id: string, multi?: boolean) => void;
  open: boolean;
  onToggle: () => void;
}

const regions = ["All", "华北", "东北", "华南", "西北"];

const regionColors: Record<string, string> = {
  华北: "#e63946",
  东北: "#457b9d",
  华南: "#2a9d8f",
  西北: "#e9c46a",
};

/** Build a short disambiguation label for duplicate sampleIds */
function disambiguate(s: Sample): string {
  const parts: string[] = [];
  if (s.rockType) parts.push(s.rockType.slice(0, 4));
  if (s.ageMa != null) parts.push(`${s.ageMa}Ma`);
  if (s.ageType && s.ageType !== "Weighted average age") {
    parts.push(s.ageType === "Concordia age" ? "Conc" : s.ageType.slice(0, 4));
  }
  return parts.join(" · ");
}

export default function Sidebar({ samples, selectedIds, onSelect, open, onToggle }: SidebarProps) {
  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("All");
  const [collapsedRefs, setCollapsedRefs] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [ageRange, setAgeRange] = useState<[number, number]>([0, 350]);

  const toggleRef = (ref: string) => {
    setCollapsedRefs((prev) => {
      const next = new Set(prev);
      if (next.has(ref)) next.delete(ref);
      else next.add(ref);
      return next;
    });
  };

  const allAges = useMemo(() => {
    return samples.filter((s) => s.ageMa != null).map((s) => s.ageMa!) as number[];
  }, [samples]);

  const ageMin = allAges.length > 0 ? Math.floor(Math.min(...allAges) / 10) * 10 : 0;
  const ageMax = allAges.length > 0 ? Math.ceil(Math.max(...allAges) / 10) * 10 : 350;

  const filtered = useMemo(() => {
    return samples.filter((s) => {
      if (region !== "All" && s.region !== region) return false;
      if (s.ageMa != null && (s.ageMa < ageRange[0] || s.ageMa > ageRange[1])) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          s.sampleId.toLowerCase().includes(q) ||
          s.formation.toLowerCase().includes(q) ||
          s.basin.toLowerCase().includes(q) ||
          s.rockType.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [samples, search, region, ageRange]);

  const grouped = useMemo(() => clusterSamples(filtered), [filtered]);

  // When all refs use the same paper, auto-expand
  const singlePaper = grouped.length === 1;
  const effectiveCollapsed = singlePaper ? new Set<string>() : collapsedRefs;

  // Count duplicates per sampleId within the filtered set
  const sampleIdCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of filtered) {
      counts.set(s.sampleId, (counts.get(s.sampleId) || 0) + 1);
    }
    return counts;
  }, [filtered]);

  return (
    <div className="relative h-full">
      {/* Toggle button (always visible) */}
      <button
        onClick={onToggle}
        className="absolute top-3 z-[1001] w-8 h-8 rounded-lg bg-white/80 backdrop-blur-md
          flex items-center justify-center shadow-sm border border-black/5
          hover:bg-white transition-all"
        style={{ right: open ? "-40px" : "-44px" }}
        title={open ? "收起侧栏" : "展开侧栏"}
      >
        {open
          ? <PanelLeftClose className="w-4 h-4 text-secondary-label" />
          : <PanelLeftOpen className="w-4 h-4 text-secondary-label" />
        }
      </button>

      {/* Drawer */}
      <div
        className="h-full flex flex-col bg-white/80 backdrop-blur-xl border-r border-black/5
          ios-transition overflow-hidden"
        style={{
          width: open ? "320px" : "0px",
          minWidth: open ? "320px" : "0px",
        }}
      >
        {/* Header */}
        <div className="px-5 pt-5 pb-3 flex-shrink-0">
          <h2 className="text-[18px] font-semibold text-foreground flex items-center gap-2 tracking-tight">
            <Layers className="w-5 h-5 text-accent" />
            GeoViz
          </h2>
          <p className="text-[12px] text-secondary-label mt-1">
            {filtered.length} of {samples.length} samples
          </p>
        </div>

        {/* Search */}
        <div className="px-4 pb-2 flex-shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-tertiary-label" />
            <input
              type="text"
              placeholder="Search samples…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-[14px] bg-grouped-bg rounded-xl
                border-none focus:outline-none focus:ring-2 focus:ring-accent/30
                placeholder:text-tertiary-label"
            />
          </div>
        </div>

        {/* Region filter */}
        <div className="flex gap-1.5 px-4 pb-2 flex-shrink-0 overflow-x-auto">
          {regions.map((r) => (
            <button
              key={r}
              onClick={() => setRegion(r)}
              className={`px-3 py-1.5 text-[12px] rounded-full whitespace-nowrap transition-all ${
                region === r
                  ? "bg-foreground text-white font-medium"
                  : "bg-grouped-bg text-secondary-label hover:bg-black/5"
              }`}
            >
              {r !== "All" && (
                <span
                  className="inline-block w-2 h-2 rounded-full mr-1"
                  style={{ background: regionColors[r] }}
                />
              )}
              {r}
            </button>
          ))}
        </div>

        {/* Filter toggle + Age range slider */}
        <div className="px-4 pb-2 flex-shrink-0">
          <button
            onClick={() => setShowFilters((v) => !v)}
            className="flex items-center gap-1.5 text-[11px] text-secondary-label hover:text-foreground transition-colors"
          >
            <SlidersHorizontal className="w-3 h-3" />
            {showFilters ? "Hide filters" : "More filters"}
          </button>

          {showFilters && (
            <div className="mt-2 space-y-2">
              <div>
                <div className="flex justify-between text-[10px] text-tertiary-label mb-1">
                  <span>Age range</span>
                  <span>{ageRange[0]}–{ageRange[1]} Ma</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={ageMin}
                    max={ageMax}
                    step={5}
                    value={ageRange[0]}
                    onChange={(e) => {
                      const v = parseInt(e.target.value);
                      setAgeRange(([lo, hi]) => [Math.min(v, hi - 5), hi]);
                    }}
                    className="flex-1 accent-accent"
                  />
                  <input
                    type="range"
                    min={ageMin}
                    max={ageMax}
                    step={5}
                    value={ageRange[1]}
                    onChange={(e) => {
                      const v = parseInt(e.target.value);
                      setAgeRange(([lo, hi]) => [lo, Math.max(v, lo + 5)]);
                    }}
                    className="flex-1 accent-accent"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sample list */}
        <div className="flex-1 overflow-y-auto px-3 pb-3">
          {grouped.map((refGroup: ReferenceGroup) => {
            const isCollapsed = effectiveCollapsed.has(refGroup.reference);
            return (
              <div key={refGroup.reference} className="mb-2">
                {/* Reference header */}
                {grouped.length > 1 && (
                  <button
                    onClick={() => toggleRef(refGroup.reference)}
                    className="w-full flex items-center gap-1.5 px-1 py-1.5 text-[11px] text-tertiary-label
                      hover:text-secondary-label transition-colors"
                  >
                    {isCollapsed
                      ? <ChevronRight className="w-3 h-3 flex-shrink-0" />
                      : <ChevronDown className="w-3 h-3 flex-shrink-0" />
                    }
                    <BookOpen className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{refGroup.shortRef}</span>
                    <span className="flex-shrink-0">({refGroup.samples.length})</span>
                  </button>
                )}

                {!isCollapsed && (
                  <div className="pl-4 border-l-2 border-black/5">
                    {refGroup.clusters.map((cluster) => (
                  <div key={cluster.prefix} className="mb-0.5">
                    {/* Separator between prefix groups within same paper */}
                    {refGroup.clusters.length > 1 && (
                      <div className="px-1 py-0.5">
                        <span className="text-[10px] text-tertiary-label/60 ml-7">
                          {cluster.prefix}
                        </span>
                      </div>
                    )}
                    {cluster.samples.map((s) => {
                      const active = selectedIds.includes(s.id);
                      const isDup = (sampleIdCounts.get(s.sampleId) || 1) > 1;
                      const disambig = isDup ? disambiguate(s) : "";
                      return (
                        <button
                          key={s.id}
                          onClick={(e) => onSelect(s.id, e.metaKey || e.ctrlKey)}
                          className={`w-full text-left p-3 rounded-xl mb-0.5 transition-all ${
                            active
                              ? "bg-accent-light ring-1 ring-accent/20"
                              : "hover:bg-black/[0.03]"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {selectedIds.length > 0 && (
                              <span
                                className={`w-4 h-4 rounded flex-shrink-0 flex items-center justify-center text-[10px] border transition-all ${
                                  active
                                    ? "bg-accent border-accent text-white"
                                    : "border-black/15 bg-white"
                                }`}
                              >
                                {active && "✓"}
                              </span>
                            )}
                            <span
                              className="w-2 h-2 rounded-full flex-shrink-0"
                              style={{ background: regionColors[s.region] }}
                            />
                            <span className="font-medium text-[14px] text-foreground truncate">
                              {s.sampleId}
                            </span>
                            {isDup && disambig && (
                              <span className="text-[10px] text-tertiary-label truncate max-w-[80px]">
                                {disambig}
                              </span>
                            )}
                            {s.ageMa != null && (
                              <span className="ml-auto text-[12px] text-accent flex items-center gap-0.5 flex-shrink-0 font-medium">
                                <Clock className="w-3 h-3" />
                                {s.ageMa}
                              </span>
                            )}
                          </div>
                          <div className="ml-[14px] text-[12px] text-secondary-label mt-0.5 flex items-center gap-1">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{s.basin} · {s.formation}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ))}
                  </div>
                )}
              </div>
            );
          })}
          {filtered.length === 0 && (
            <p className="text-center text-[13px] text-tertiary-label py-12">No results</p>
          )}
        </div>
      </div>
    </div>
  );
}
