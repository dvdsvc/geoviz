"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Search, ChevronRight, MapPin, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import type { ProvenanceData, ProvenanceField } from "@/types/provenance";

interface ProvenanceViewerProps {
  data: ProvenanceData | null;
  activeField: ProvenanceField | null;
  getPageUrl: (page: number) => string;
  onNavigate: (field: ProvenanceField) => void;
  onClose: () => void;
}

export default function ProvenanceViewer({
  data,
  activeField,
  getPageUrl,
  onNavigate,
  onClose,
}: ProvenanceViewerProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const types = useMemo(
    () => data ? [...new Set(data.provenances.map((p) => p.data_type))] : [],
    [data]
  );

  const groups = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, { data_type: string; record_id: string; fields: ProvenanceField[] }>();
    for (const p of data.provenances) {
      if (typeFilter !== "all" && p.data_type !== typeFilter) continue;
      if (
        search &&
        !p.record_id.toLowerCase().includes(search.toLowerCase()) &&
        !p.label.toLowerCase().includes(search.toLowerCase()) &&
        !(p.display || "").toLowerCase().includes(search.toLowerCase())
      )
        continue;
      const key = `${p.data_type}|${p.record_id}`;
      if (!map.has(key)) {
        map.set(key, { data_type: p.data_type, record_id: p.record_id, fields: [] });
      }
      map.get(key)!.fields.push(p);
    }
    return [...map.values()];
  }, [data, typeFilter, search]);

  // Scroll to and highlight the active field
  useEffect(() => {
    if (!activeField?.page) return;
    const wrapper = document.getElementById(`pv-page-${activeField.page}`);
    if (wrapper) {
      wrapper.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    // Draw highlight after scroll
    const timer = setTimeout(() => drawHighlight(activeField), 600);
    return () => clearTimeout(timer);
  }, [activeField]);

  const drawHighlight = useCallback(
    (field: ProvenanceField) => {
      // Clear old highlights
      document.querySelectorAll(".pv-highlight-box").forEach((b) => b.remove());

      if (!field.page || !field.bbox_norm) return;
      const wrapper = document.getElementById(`pv-page-${field.page}`);
      if (!wrapper) return;
      const img = wrapper.querySelector("img");
      if (!img) return;

      const displayW = img.clientWidth;
      const displayH = img.clientHeight;
      const [nx0, ny0, nx1, ny1] = field.bbox_norm;

      const box = document.createElement("div");
      box.className = "pv-highlight-box";
      box.style.cssText = `
        position: absolute;
        left: ${nx0 * displayW}px;
        top: ${ny0 * displayH}px;
        width: ${Math.max((nx1 - nx0) * displayW, 4)}px;
        height: ${Math.max((ny1 - ny0) * displayH, 4)}px;
        background: rgba(0, 122, 255, 0.35);
        border: 2px solid #007aff;
        border-radius: 2px;
        pointer-events: none;
        z-index: 10;
        animation: pv-pulse 0.5s ease-in-out;
      `;
      wrapper.appendChild(box);
      setTimeout(() => {
        box.style.opacity = "0.25";
      }, 6000);
    },
    []
  );

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center bg-grouped-bg">
        <p className="text-[14px] text-tertiary-label">Loading provenance data…</p>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-grouped-bg">
      <style>{`
        @keyframes pv-pulse {
          0% { background: rgba(0, 122, 255, 0.6); }
          100% { background: rgba(0, 122, 255, 0.35); }
        }
      `}</style>

      {/* Sidebar */}
      <div className="relative flex-shrink-0 h-full">
        <button
          onClick={() => setSidebarOpen((v) => !v)}
          className="absolute top-3 z-10 w-8 h-8 rounded-lg bg-white/80 backdrop-blur-md
            flex items-center justify-center shadow-sm border border-black/5
            hover:bg-white transition-all"
          style={{ right: sidebarOpen ? "-36px" : "-40px" }}
          title={sidebarOpen ? "收起侧栏" : "展开侧栏"}
        >
          {sidebarOpen ? (
            <PanelLeftClose className="w-4 h-4 text-secondary-label" />
          ) : (
            <PanelLeftOpen className="w-4 h-4 text-secondary-label" />
          )}
        </button>

        <div
          className="h-full flex flex-col bg-white/80 backdrop-blur-xl border-r border-black/5
            ios-transition overflow-hidden"
          style={{
            width: sidebarOpen ? "260px" : "0px",
            minWidth: sidebarOpen ? "260px" : "0px",
          }}
        >
          {/* Header */}
          <div className="px-4 pt-4 pb-2 flex-shrink-0">
            <h3 className="text-[13px] font-semibold text-foreground truncate">
              {data.paper_name.split("_")[0]}
            </h3>
            <p className="text-[10px] text-tertiary-label mt-0.5">
              {data.found_count}/{data.total_fields} · {data.total_pages}p
            </p>
          </div>

          {/* Filters */}
          <div className="px-3 pb-2 flex flex-col gap-1.5 flex-shrink-0">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-tertiary-label" />
              <input
                type="text"
                placeholder="搜索..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-7 pr-2 py-1.5 text-[11px] bg-grouped-bg rounded-lg
                  border-none focus:outline-none focus:ring-1 focus:ring-accent/30
                  placeholder:text-tertiary-label"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="text-[10px] px-2 py-1 rounded-md bg-grouped-bg border-none text-secondary-label focus:outline-none"
            >
              <option value="all">全部类型</option>
              {types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Record list */}
          <div className="flex-1 overflow-y-auto px-2 pb-2">
            {groups.map((g) => {
              const foundCount = g.fields.filter((f) => f.page).length;
              return (
                <div key={`${g.data_type}|${g.record_id}`} className="mb-1">
                  <div className="px-2 py-1 rounded-md bg-black/[0.02] flex items-center justify-between">
                    <span className="text-[11px] font-medium text-foreground truncate">
                      {g.record_id}
                    </span>
                    <span className="text-[9px] text-tertiary-label ml-1 flex-shrink-0">
                      {foundCount}/{g.fields.length}
                    </span>
                  </div>
                  {g.fields.map((f, fi) => {
                    const isActive =
                      activeField?.data_type === f.data_type &&
                      activeField?.record_id === f.record_id &&
                      activeField?.label === f.label;
                    return (
                      <button
                        key={fi}
                        onClick={() => f.page && onNavigate(f)}
                        disabled={!f.page}
                        className={`w-full text-left px-2 py-1 flex items-center gap-1.5 rounded transition-colors ${
                          isActive
                            ? "bg-accent-light"
                            : f.page
                            ? "hover:bg-black/[0.02]"
                            : "opacity-35"
                        }`}
                      >
                        <span className="text-[10px] text-secondary-label flex-shrink-0 w-[56px] truncate">
                          {f.label}
                        </span>
                        <span className="text-[10px] text-foreground truncate flex-1">
                          {(f.display || "").substring(0, 24)}
                        </span>
                        {f.page ? (
                          <span className="text-[9px] text-accent font-medium flex-shrink-0">
                            p.{f.page}
                          </span>
                        ) : (
                          <span className="text-[9px] text-tertiary-label flex-shrink-0">—</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* PDF pages area */}
      <div
        ref={containerRef}
        className="flex-1 h-full overflow-y-auto py-4 flex flex-col items-center relative"
        style={{ background: "#525659" }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="fixed top-4 right-4 z-50 w-10 h-10 rounded-full
            bg-white/90 backdrop-blur-md shadow-lg
            flex items-center justify-center
            hover:bg-white transition-colors"
          title="返回地图"
        >
          <X className="w-4.5 h-4.5 text-secondary-label" />
        </button>
        {data.page_images.map((pi) => (
          <div key={pi.page} className="mb-2">
            <div className="text-[10px] text-gray-400 text-center py-1">
              第 {pi.page} 页
            </div>
            <div
              id={`pv-page-${pi.page}`}
              className="relative bg-white shadow-lg"
              style={{ lineHeight: 0 }}
            >
              <img
                src={getPageUrl(pi.page)}
                alt={`Page ${pi.page}`}
                className="block max-w-full"
                style={{ maxHeight: "none" }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
