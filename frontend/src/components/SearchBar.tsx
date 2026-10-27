"use client";

import { useState, useRef, useEffect } from "react";
import { Loader2 } from "lucide-react";

/** Strip markdown artifacts from RAG answer and return safe HTML. */
function formatAnswer(md: string): string {
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>") // bold
    .replace(/^[-•]\s+/gm, "· ")                       // bullet
    .replace(/\n{2,}/g, "<br/><br/>")                   // paragraph break
    .replace(/\n/g, "<br/>")                            // line break
    .trim();
}

interface MatchedSample {
  sampleId: string;
  region: string;
  basin: string;
  formation: string;
  rockType: string;
  ageMa: number | null;
  error: number | null;
}

interface SearchBarProps {
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  onSelectSample?: (sampleId: string) => void;
}

export default function SearchBar({ expanded, onExpandedChange, onSelectSample }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [matchedSamples, setMatchedSamples] = useState<MatchedSample[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        onExpandedChange(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onExpandedChange]);

  async function handleSearch() {
    const q = query.trim();
    if (!q || loading) return;
    onExpandedChange(true);
    setLoading(true);
    setAnswer(null);
    setMatchedSamples([]);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();
      setAnswer(data.answer || "No answer returned.");
      setMatchedSamples(data.matched_samples || []);
    } catch {
      setAnswer("Cannot connect to backend. Make sure the server is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div ref={wrapperRef} className="relative w-full max-w-[600px] mx-auto">
      {/* Search bar */}
      <div
        className={`
          flex items-center px-6 py-4
          bg-white
          border border-black/8
          transition-all duration-200
          ${expanded
            ? "rounded-t-2xl shadow-[0_6px_40px_rgba(0,0,0,0.15)]"
            : "rounded-full shadow-[0_4px_24px_rgba(0,0,0,0.10)] hover:shadow-[0_6px_32px_rgba(0,0,0,0.15)]"
          }
        `}
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (answer) onExpandedChange(true); }}
          onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
          placeholder="Search geological samples…"
          className="flex-1 text-[16px] font-medium bg-transparent outline-none placeholder:text-black/25 text-foreground tracking-[-0.01em]"
        />

        {loading && (
          <Loader2 className="w-4 h-4 text-black/20 animate-spin flex-shrink-0" />
        )}
      </div>

      {/* Dropdown answer */}
      {expanded && (answer || loading) && (
        <div
          className="
            absolute top-full left-0 right-0
            bg-white
            border border-t-0 border-black/8
            rounded-b-2xl
            shadow-[0_12px_40px_rgba(0,0,0,0.12)]
            max-h-[360px] overflow-y-auto
          "
        >
          <div className="px-6 py-4">
            {loading ? (
              <div className="flex items-center gap-3 py-4 justify-center">
                <Loader2 className="w-4 h-4 text-black/20 animate-spin" />
                <span className="text-[14px] text-black/40">Searching…</span>
              </div>
            ) : answer ? (
              <>
                <div
                  className="text-[13px] text-foreground/80 leading-[1.7] space-y-2"
                  style={{ fontFamily: '"Noto Sans SC", "SF Pro Text", system-ui, sans-serif' }}
                  dangerouslySetInnerHTML={{ __html: formatAnswer(answer) }}
                />

              {matchedSamples.length > 0 && (
                <div className="mt-3 pt-3 border-t border-black/5 space-y-1.5">
                  {matchedSamples.map((s) => {
                    const ageLabel =
                      s.ageMa != null ? `${s.ageMa} Ma${s.error ? " ± " + s.error : ""}` : "";
                    return (
                      <button
                        key={s.sampleId}
                        onClick={() => onSelectSample?.(s.sampleId)}
                        className="
                          w-full flex items-center gap-3 px-3 py-2 rounded-lg
                          bg-black/[0.02] hover:bg-black/[0.05]
                          transition-colors text-left group
                        "
                      >
                        <span className="text-[14px] font-semibold text-foreground tracking-tight flex-shrink-0">
                          {s.sampleId}
                        </span>
                        <span className="text-[11px] text-black/40 truncate">
                          {s.basin} · {s.formation} · {s.rockType}
                        </span>
                        {ageLabel && (
                          <span className="ml-auto text-[11px] font-medium text-[#007aff] flex-shrink-0">
                            {ageLabel}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
