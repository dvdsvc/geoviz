"use client";

import { useState, useEffect, useMemo } from "react";
import { SpotRecord } from "@/utils/spotCalc";
import realSpotsRaw from "@/data/realSpots.json";
import { samples } from "@/data/samples";

export function useSpots() {
  const [data, setData] = useState<Record<string, SpotRecord[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const grouped: Record<string, SpotRecord[]> = {};
    const records = realSpotsRaw as SpotRecord[];
    for (const r of records) {
      const sid = r.sample_id;
      if (!grouped[sid]) grouped[sid] = [];
      grouped[sid].push({ ...r, s_discarded: r.s_discarded ?? false });
    }

    if (!cancelled) {
      setData(grouped);
      setLoading(false);
    }

    return () => { cancelled = true; };
  }, []);

  // Dynamically compute nGrains from actual data (single source of truth)
  const sampleNGrains = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const [sid, spots] of Object.entries(data)) {
      counts[sid] = spots.length;
    }
    return counts;
  }, [data]);

  // Update samples with correct nGrains from data
  const updatedSamples = useMemo(() =>
    samples.map(s => ({
      ...s,
      nGrains: sampleNGrains[s.sampleId] ?? 0,
    })),
    [sampleNGrains]
  );

  return { data, loading, setData, updatedSamples };
}
