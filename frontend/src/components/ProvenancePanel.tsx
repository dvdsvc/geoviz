"use client";

import { useMemo, useState } from "react";
import { X, FileSearch, MapPin, ChevronRight, Eye, EyeOff } from "lucide-react";
import type { ProvenanceData, ProvenanceField } from "@/types/provenance";

interface ProvenancePanelProps {
  data: ProvenanceData;
  activeField: ProvenanceField | null;
  viewerOpen: boolean;
  onToggleViewer: () => void;
  onNavigate: (field: ProvenanceField) => void;
  onClose: () => void;
}

export default function ProvenancePanel({
  data,
  activeField,
  viewerOpen,
  onToggleViewer,
  onNavigate,
  onClose,
}: ProvenancePanelProps) {
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");

  const types = useMemo(
    () => [...new Set(data.provenances.map((p) => p.data_type))],
    [data]
  );

  const groups = useMemo(() => {
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

  return (
    <div className="ios-card overflow-hidden max-h-[calc(100vh-160px)] flex flex-col">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSearch className="w-4 h-4 text-accent" />
            <span className="text-[13px] font-medium text-accent">原文定位</span>
          </div>
          <button
            onClick={onClose}
            className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10"
          >
            <X className="w-3.5 h-3.5 text-secondary-label" />
          </button>
        </div>
        <h3 className="text-[15px] font-semibold text-foreground mt-2 leading-snug">
          {data.paper_name.split("_")[0]}
        </h3>
        <p className="text-[12px] text-secondary-label mt-1">
          {data.found_count}/{data.total_fields} 已定位 · {data.total_pages} 页
        </p>
      </div>

      {/* Filter bar */}
      <div className="px-4 pb-2 flex gap-2 flex-shrink-0">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="text-[11px] px-2 py-1.5 rounded-lg bg-grouped-bg border-none text-secondary-label focus:outline-none"
        >
          <option value="all">全部类型</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="搜索 sample_id / 字段..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 text-[11px] px-2 py-1.5 rounded-lg bg-grouped-bg border-none text-foreground placeholder:text-tertiary-label focus:outline-none focus:ring-1 focus:ring-accent/30"
        />
      </div>

      {/* Toggle viewer */}
      <div className="px-4 pb-2 flex-shrink-0">
        <button
          onClick={onToggleViewer}
          className={`w-full flex items-center justify-center gap-2 py-2 rounded-xl text-[12px] font-medium transition-colors ${
            viewerOpen
              ? "bg-accent-light text-accent"
              : "bg-grouped-bg text-secondary-label hover:bg-black/5"
          }`}
        >
          {viewerOpen ? (
            <>
              <EyeOff className="w-3.5 h-3.5" />
              关闭原文对照
            </>
          ) : (
            <>
              <Eye className="w-3.5 h-3.5" />
              原文对照阅读
            </>
          )}
        </button>
      </div>

      {/* Field list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {groups.length === 0 ? (
          <p className="text-[13px] text-tertiary-label text-center py-8">无匹配记录</p>
        ) : (
          groups.map((g) => {
            const foundCount = g.fields.filter((f) => f.page).length;
            return (
              <div key={`${g.data_type}|${g.record_id}`} className="mb-2">
                {/* Group header */}
                <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-grouped-bg">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-[12px] font-semibold text-foreground truncate">
                      {g.record_id}
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent text-white flex-shrink-0">
                      {g.data_type}
                    </span>
                  </div>
                  <span className="text-[10px] text-tertiary-label flex-shrink-0 ml-2">
                    {foundCount}/{g.fields.length}
                  </span>
                </div>
                {/* Fields */}
                <div className="mt-0.5">
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
                        className={`w-full text-left px-3 py-1.5 rounded-lg flex items-center justify-between gap-2 transition-colors ${
                          isActive
                            ? "bg-accent-light ring-1 ring-accent/20"
                            : f.page
                            ? "hover:bg-black/[0.03]"
                            : "opacity-40"
                        }`}
                      >
                        <span className="text-[11px] text-secondary-label flex-shrink-0 min-w-[72px]">
                          {f.label}
                        </span>
                        <span className="text-[11px] text-foreground truncate flex-1">
                          {(f.display || "").substring(0, 40)}
                        </span>
                        {f.page ? (
                          <span className="text-[10px] text-accent font-medium flex-shrink-0 flex items-center gap-0.5">
                            <MapPin className="w-2.5 h-2.5" />
                            p.{f.page}
                          </span>
                        ) : (
                          <span className="text-[10px] text-tertiary-label flex-shrink-0">—</span>
                        )}
                        <ChevronRight className="w-3 h-3 text-tertiary-label flex-shrink-0" />
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
