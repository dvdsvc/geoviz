"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import { useSpots } from "@/hooks/useSpots";
import Sidebar from "@/components/Sidebar";
import SampleDetail from "@/components/SampleDetail";
import SearchBar from "@/components/SearchBar";
import ProvenanceViewer from "@/components/ProvenanceViewer";
import { useProvenanceData, useProvenanceList } from "@/hooks/useProvenance";
import type { ProvenanceField } from "@/types/provenance";
import { Clock } from "lucide-react";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-grouped-bg">
      <p className="text-tertiary-label text-[14px]">Loading map…</p>
    </div>
  ),
});

const TimelineDrawer = dynamic(() => import("@/components/TimelineDrawer"), { ssr: false });
const ConcordiaPlot = dynamic(() => import("@/components/ConcordiaPlot"), { ssr: false });
const WeightedMeanPlot = dynamic(() => import("@/components/WeightedMeanPlot"), { ssr: false });
const StratColumn = dynamic(() => import("@/components/StratColumn"), { ssr: false });
const ComparePanel = dynamic(() => import("@/components/ComparePanel"), { ssr: false });
const SpotTable = dynamic(() => import("@/components/SpotTable"), { ssr: false });

type RightPanel = "detail" | "concordia" | "weightedMean" | "stratColumn" | "compare" | "spots" | null;

export default function Home() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [rightPanel, setRightPanel] = useState<RightPanel>(null);
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const { data: spotsData, setData: setSpotsData, updatedSamples: samples } = useSpots();
  const { papers: provenancePapers } = useProvenanceList();

  // Dynamic set of papers that have provenance — updated automatically from backend
  const papersWithProvenance = new Set(provenancePapers.map((p) => p.paper_name));

  const getPaperNameForSample = useCallback(
    (sample: { reference?: string } | null): string | null => {
      if (!sample?.reference) return null;
      if (papersWithProvenance.has(sample.reference)) {
        return sample.reference;
      }
      // Fuzzy match: try to find a provenance paper whose name or short_name
      // partially matches the reference (case-insensitive substring)
      const ref = sample.reference.toLowerCase();
      for (const p of provenancePapers) {
        const pn = p.paper_name.toLowerCase();
        const sn = p.short_name.toLowerCase();
        if (pn.includes(ref) || sn.includes(ref) || ref.includes(sn)) {
          return p.paper_name;
        }
      }
      return null;
    },
    [papersWithProvenance, provenancePapers]
  );

  // ── Provenance state ──
  const [provenancePaper, setProvenancePaper] = useState<string | null>(null);
  const [provenanceActiveField, setProvenanceActiveField] = useState<ProvenanceField | null>(null);
  const [provenanceViewerOpen, setProvenanceViewerOpen] = useState(false);
  const { data: provenanceData, getPageUrl } = useProvenanceData(provenancePaper);

  const selected = selectedIds.length === 1
    ? samples.find((s) => s.id === selectedIds[0]) || null
    : null;

  const selectedSamples = selectedIds
    .map((id) => samples.find((s) => s.id === id))
    .filter(Boolean) as typeof samples;

  const handleSelect = useCallback((id: string, multi?: boolean) => {
    setSelectedIds((prev) => {
      let next: string[];

      if (multi) {
        if (prev.includes(id)) {
          next = prev.filter((x) => x !== id);
        } else if (prev.length < 4) {
          next = [...prev, id];
        } else {
          return prev;
        }
      } else {
        if (prev.length === 1 && prev[0] === id) {
          next = [];
        } else {
          next = [id];
        }
      }

      if (next.length === 0) {
        setRightPanel(null);
      } else if (next.length >= 2) {
        setRightPanel("compare");
      } else {
        setRightPanel("detail");
      }

      return next;
    });
  }, []);

  const handleCloseRight = useCallback(() => {
    setRightPanel(null);
    setSelectedIds([]);
  }, []);

  const handleConcordia = useCallback(() => {
    setRightPanel("concordia");
  }, []);

  const handleSelectSampleBySampleId = useCallback((sampleId: string) => {
    const match = samples.find((s) => s.sampleId === sampleId);
    if (match) {
      setSelectedIds([match.id]);
      setRightPanel("detail");
    }
  }, []);

  const handleWeightedMean = useCallback(() => {
    setRightPanel("weightedMean");
  }, []);

  const handleStratColumn = useCallback(() => {
    setRightPanel("stratColumn");
  }, []);

  const handleSpots = useCallback(() => {
    setRightPanel("spots");
  }, []);

  // ── Provenance: open viewer directly (no intermediate panel) ──
  const handleViewInSource = useCallback((paperName: string) => {
    setProvenancePaper(paperName);
    setProvenanceActiveField(null);
    setProvenanceViewerOpen(true);
    setRightPanel(null); // close the right card
  }, []);

  const handleProvenanceClose = useCallback(() => {
    setProvenanceViewerOpen(false);
    // Restore the detail card if a sample is selected
    if (selectedIds.length === 1) {
      setRightPanel("detail");
    }
  }, [selectedIds]);

  const handleProvenanceNavigate = useCallback((field: ProvenanceField) => {
    setProvenanceActiveField(field);
  }, []);

  const handleUpdateSpots = useCallback((sampleId: string, updatedSpots: typeof spotsData[string]) => {
    setSpotsData((prev) => ({ ...prev, [sampleId]: updatedSpots }));
  }, [setSpotsData]);

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      {/* Sidebar drawer */}
      <aside className="flex-shrink-0 h-full relative z-[1000]">
        <Sidebar
          samples={samples}
          selectedIds={selectedIds}
          onSelect={handleSelect}
          open={sidebarOpen}
          onToggle={() => setSidebarOpen((v) => !v)}
        />
      </aside>

      {/* Map / Globe / Provenance area */}
      <main className="flex-1 relative">
        <AnimatePresence>
          {provenanceViewerOpen ? (
            <motion.div
              key="provenance-viewer"
              initial={{ x: "100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0 }}
              transition={{
                type: "spring",
                stiffness: 120,
                damping: 18,
                mass: 0.8,
              }}
              className="absolute inset-0 z-[900]"
            >
              <ProvenanceViewer
                data={provenanceData}
                activeField={provenanceActiveField}
                getPageUrl={getPageUrl}
                onNavigate={handleProvenanceNavigate}
                onClose={handleProvenanceClose}
              />
            </motion.div>
          ) : (
            <motion.div
              key="map-area"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0"
            >
              <MapView
                samples={samples}
                selectedIds={selectedIds}
                onSelect={handleSelect}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* AI Search Bar — top center, Google-style (hidden in provenance mode) */}
        {!provenanceViewerOpen && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1100] w-full px-16 pointer-events-none">
            <div className="pointer-events-auto">
              <SearchBar
                expanded={searchExpanded}
                onExpandedChange={setSearchExpanded}
                onSelectSample={handleSelectSampleBySampleId}
              />
            </div>
          </div>
        )}

        {/* KPI Cards (hidden in provenance mode) */}
        {/* Legend (hidden in provenance mode) */}
        {!provenanceViewerOpen && (
          <div
            className="absolute left-5 ios-card px-4 py-3 z-[999] ios-transition"
            style={{ bottom: timelineOpen ? 195 : 20 }}
          >
            <p className="text-[11px] font-semibold text-tertiary-label uppercase tracking-wider mb-2">
              Regions
            </p>
            {[
              { name: "华北 North China", color: "#e63946" },
              { name: "东北 NE China", color: "#457b9d" },
              { name: "华南 South China", color: "#2a9d8f" },
              { name: "西北 NW China", color: "#e9c46a" },
            ].map((r) => (
              <div
                key={r.name}
                className="flex items-center gap-2 text-[12px] text-secondary-label py-0.5"
              >
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ background: r.color }}
                />
                {r.name}
              </div>
            ))}
          </div>
        )}

        {/* Right panel: sample detail / source passage / concordia / compare */}
        {rightPanel && (
          <div className="absolute top-16 right-4 z-[1200] ios-transition">
            {rightPanel === "compare" && selectedSamples.length >= 2 && (
              <ComparePanel
                samples={selectedSamples}
                onClose={handleCloseRight}
                onRemove={(id) => handleSelect(id, true)}
              />
            )}

            {selected && rightPanel === "detail" && (
              <div style={{ width: 360 }}>
                <SampleDetail
                  sample={selected}
                  onClose={handleCloseRight}
                  onConcordia={handleConcordia}
                  onWeightedMean={handleWeightedMean}
                  onStratColumn={handleStratColumn}
                  onSpots={handleSpots}
                  hasSource={!!getPaperNameForSample(selected)}
                  onViewInSource={() => {
                    const pn = getPaperNameForSample(selected);
                    if (pn) handleViewInSource(pn);
                  }}
                />
              </div>
            )}
            {selected && rightPanel === "concordia" && (
              <div style={{ width: 360 }}>
                <ConcordiaPlot
                  sample={selected}
                  spots={spotsData[selected.sampleId] || []}
                  onClose={handleCloseRight}
                />
              </div>
            )}
            {selected && rightPanel === "weightedMean" && (
              <div style={{ width: 360 }}>
                <WeightedMeanPlot
                  sample={selected}
                  spots={spotsData[selected.sampleId] || []}
                  onClose={handleCloseRight}
                />
              </div>
            )}
            {selected && rightPanel === "stratColumn" && (
              <div style={{ width: 360 }}>
                <StratColumn
                  sample={selected}
                  onClose={handleCloseRight}
                />
              </div>
            )}
            {selected && rightPanel === "spots" && spotsData[selected.sampleId] && (
              <SpotTable
                sample={selected}
                spots={spotsData[selected.sampleId]}
                onClose={handleCloseRight}
                onUpdateSpots={handleUpdateSpots}
              />
            )}
          </div>
        )}

        {/* Bottom-right buttons (hidden in provenance mode) */}
        {!provenanceViewerOpen && (
          <div
            className="absolute right-5 z-[1000] flex items-center gap-2 ios-transition"
            style={{ bottom: timelineOpen ? 195 : 20 }}
          >
            <button
              onClick={() => setTimelineOpen(!timelineOpen)}
              className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all ${
                timelineOpen
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-white/90 backdrop-blur-md text-secondary-label hover:bg-white"
              }`}
              title="Geological timeline"
            >
              <Clock className="w-4.5 h-4.5" />
            </button>
          </div>
        )}

        {/* Timeline drawer */}
        <TimelineDrawer
          samples={samples}
          selectedId={selectedIds[0] || null}
          onSelect={handleSelect}
          open={timelineOpen}
        />
      </main>

    </div>
  );
}
