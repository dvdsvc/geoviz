"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, X, MapPin, Clock, Sparkles } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  matchedSamples?: MatchedSample[];
  thinking?: boolean;
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

interface ChatPanelProps {
  onClose: () => void;
  onSelectSample?: (id: string) => void;
}

export default function ChatPanel({ onClose, onSelectSample }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I can help you explore the geochronology database.\n\nTry asking:\n· Samples from North China?\n· What is the oldest sample?\n· How many U-Pb zircon samples are there?\n· Age range of Songliao Basin samples?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    // Add thinking placeholder
    setMessages((prev) => [...prev, { role: "assistant", content: "", thinking: true }]);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await res.json();

      setMessages((prev) => {
        const updated = [...prev];
        // Replace thinking placeholder with real answer
        updated[updated.length - 1] = {
          role: "assistant",
          content: data.answer || "Sorry, I couldn't find an answer.",
          matchedSamples: data.matched_samples || [],
        };
        return updated;
      });
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content:
            "Cannot connect to backend. Please make sure the server is running on port 8000.",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full ios-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-separator flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-semibold text-[15px] text-foreground block leading-tight">Geo Assistant</span>
            <span className="text-[11px] text-tertiary-label">RAG + MiMo v2.5 Pro</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="w-6 h-6 rounded-full bg-black/5 flex items-center justify-center hover:bg-black/10"
        >
          <X className="w-3.5 h-3.5 text-secondary-label" />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2.5 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
            {/* Avatar */}
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                m.role === "user"
                  ? "bg-accent"
                  : "bg-gradient-to-br from-violet-500 to-blue-500"
              }`}
            >
              {m.role === "user"
                ? <User className="w-3.5 h-3.5 text-white" />
                : <Bot className="w-3.5 h-3.5 text-white" />
              }
            </div>

            {/* Bubble */}
            <div className={`max-w-[88%] min-w-0 ${m.role === "user" ? "text-right" : ""}`}>
              {m.thinking ? (
                <div className="bg-grouped-bg px-4 py-3 rounded-2xl rounded-tl-sm inline-flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 text-tertiary-label animate-spin" />
                  <span className="text-[13px] text-secondary-label">Searching database…</span>
                </div>
              ) : (
                <>
                  <div
                    className={`px-3.5 py-2.5 rounded-2xl text-[14px] leading-relaxed whitespace-pre-wrap ${
                      m.role === "user"
                        ? "bg-accent text-white rounded-tr-sm"
                        : "bg-grouped-bg text-foreground rounded-tl-sm"
                    }`}
                  >
                    {m.content}
                  </div>

                  {/* Matched samples cards */}
                  {m.matchedSamples && m.matchedSamples.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <p className="text-[11px] text-tertiary-label font-medium uppercase tracking-wider px-1">
                        Matched samples
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {m.matchedSamples.map((s) => (
                          <button
                            key={s.sampleId}
                            onClick={() => onSelectSample?.(s.sampleId)}
                            className="text-left bg-white border border-separator rounded-xl px-3 py-2
                              hover:border-accent/30 hover:bg-accent-light transition-all group"
                          >
                            <div className="flex items-center gap-1.5">
                              <MapPin className="w-3 h-3 text-secondary-label group-hover:text-accent transition-colors" />
                              <span className="text-[13px] font-medium text-foreground group-hover:text-accent transition-colors">
                                {s.sampleId}
                              </span>
                            </div>
                            <div className="text-[11px] text-secondary-label mt-0.5">
                              {s.basin} · {s.formation}
                            </div>
                            {s.ageMa != null && (
                              <div className="text-[12px] text-accent font-medium mt-0.5 flex items-center gap-0.5">
                                <Clock className="w-3 h-3" />
                                {s.ageMa} Ma
                              </div>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-separator flex-shrink-0">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Ask about geological samples…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            className="flex-1 px-3.5 py-2.5 text-[14px] bg-grouped-bg rounded-xl
              border-none focus:outline-none focus:ring-2 focus:ring-accent/30
              placeholder:text-tertiary-label"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="w-10 h-10 bg-accent text-white rounded-xl flex items-center justify-center
              hover:brightness-110 disabled:opacity-30 transition-all flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
