import { Sample } from "@/types";

/** Extract the alphabetic prefix of a sample ID (e.g. "WYS08-1" → "WYS", "Zj36" → "Zj") */
export function extractPrefix(sampleId: string): string {
  const m = sampleId.match(/^[A-Za-z]+/);
  return m ? m[0] : "";
}

export interface SampleCluster {
  prefix: string;
  samples: Sample[];
}

export interface ReferenceGroup {
  reference: string;
  shortRef: string; // trimmed display name
  clusters: SampleCluster[];
  samples: Sample[]; // flat list of all samples in this group
}

/** Get a short display name from a full reference string */
export function shortReference(ref: string): string {
  // Strip timestamp suffix like _20260517_161531
  return ref.replace(/_\d{8}_\d{6}$/, "");
}

/** Group samples by reference, then by prefix similarity within each reference */
export function clusterSamples(samples: Sample[]): ReferenceGroup[] {
  // 1. Group by reference
  const byRef = new Map<string, Sample[]>();
  for (const s of samples) {
    const ref = s.reference || "";
    const existing = byRef.get(ref);
    if (existing) {
      existing.push(s);
    } else {
      byRef.set(ref, [s]);
    }
  }

  const result: ReferenceGroup[] = [];

  for (const [ref, refSamples] of byRef) {
    // 2. Within reference, cluster by prefix
    const byPrefix = new Map<string, Sample[]>();
    for (const s of refSamples) {
      const prefix = extractPrefix(s.sampleId);
      const existing = byPrefix.get(prefix);
      if (existing) {
        existing.push(s);
      } else {
        byPrefix.set(prefix, [s]);
      }
    }

    // Sort clusters by prefix, then samples within each cluster by sampleId
    const clusters: SampleCluster[] = [];
    for (const [prefix, clusterSamples] of byPrefix) {
      clusterSamples.sort((a, b) => a.sampleId.localeCompare(b.sampleId, undefined, { numeric: true }));
      clusters.push({ prefix, samples: clusterSamples });
    }
    clusters.sort((a, b) => a.prefix.localeCompare(b.prefix));

    result.push({
      reference: ref,
      shortRef: shortReference(ref),
      clusters,
      samples: refSamples,
    });
  }

  // Sort by shortRef
  result.sort((a, b) => a.shortRef.localeCompare(b.shortRef));

  return result;
}
