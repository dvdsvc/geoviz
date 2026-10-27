"use client";

import { useState, useEffect, useCallback } from "react";
import type { ProvenanceData, PaperInfo } from "@/types/provenance";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useProvenanceList() {
  const [papers, setPapers] = useState<PaperInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/provenance/list`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) {
          setPapers(data.papers || []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return { papers, loading };
}

export function useProvenanceData(paperName: string | null) {
  const [data, setData] = useState<ProvenanceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [imageDims, setImageDims] = useState<Record<number, { width: number; height: number }>>({});

  useEffect(() => {
    if (!paperName) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${API_BASE}/api/provenance/${encodeURIComponent(paperName)}`)
      .then((r) => r.json())
      .then((json) => {
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [paperName]);

  const getPageUrl = useCallback(
    (page: number) => {
      if (!paperName) return "";
      const pi = data?.page_images?.find((p) => p.page === page);
      if (!pi) return "";
      return `${API_BASE}/api/provenance/${encodeURIComponent(paperName)}/pages/${pi.image}`;
    },
    [paperName, data]
  );

  return { data, loading, imageDims, setImageDims, getPageUrl };
}
