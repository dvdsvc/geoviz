#!/usr/bin/env python3
"""Combine pipeline spots JSON into a single flat JSON for the frontend.

Auto-discovers all *_spots.json files in OUTPUT_DIR. No hardcoded paper list.
When multiple versions of the same paper exist, keeps the one with the most spots.
"""

import json, os, sys, re
from collections import defaultdict

OUTPUT_DIR = 'data/private/pipeline'


def flatten(rec):
    """Flatten nested {value, err_1s} objects to _val / _err fields."""
    flat = {
        "spot_id": str(rec.get("spot_id") or ""),
        "sample_id": str(rec.get("sample_id") or ""),
        "s_discarded": bool(rec.get("s_discarded", False)),
        "u_ppm": rec.get("u_ppm"),
        "th_ppm": rec.get("th_ppm"),
        "th_u_ratio": rec.get("th_u_ratio"),
    }
    for key in ("r206_238", "r207_235", "r207_206", "age_206_238", "age_207_235"):
        obj = rec.get(key) or {}
        flat[f"{key}_val"] = obj.get("value")
        flat[f"{key}_err"] = obj.get("err_1s")
    age_206 = flat.get("age_206_238_val")
    age_207 = flat.get("age_207_235_val")
    if age_206 and age_207 and age_207 != 0:
        flat["concordance"] = round((age_206 / age_207) * 100, 2)
    else:
        flat["concordance"] = None
    return flat


TIMESTAMP_RE = re.compile(r"_\d{8}_\d{6}$")

def paper_base(fn: str) -> str:
    """Strip _spots.json suffix and optional _YYYYMMDD_HHMMSS timestamp."""
    name = fn[:-len("_spots.json")]  # remove _spots.json
    m = TIMESTAMP_RE.search(name)
    if m:
        return name[:m.start()]
    return name


def discover():
    """Scan OUTPUT_DIR for all *_spots.json files. Deduplicate by base name."""
    if not os.path.isdir(OUTPUT_DIR):
        print(f"ERROR: directory not found: {OUTPUT_DIR}", file=sys.stderr)
        return []

    # Group by base name, keep only the file with most spots per group.
    # Sort descending so timestamped versions (newer pipeline runs) come first,
    # breaking ties in favor of the latest run.
    groups: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for fn in sorted(os.listdir(OUTPUT_DIR), reverse=True):
        if not fn.endswith("_spots.json"):
            continue
        path = os.path.join(OUTPUT_DIR, fn)
        try:
            with open(path) as f:
                n_spots = len(json.load(f))
        except Exception:
            n_spots = 0
        base = paper_base(fn)
        groups[base].append((fn, path, n_spots))

    candidates = []
    for base, files in groups.items():
        # Keep the file with the most spots (latest pipeline run usually has more)
        best = max(files, key=lambda x: x[2])
        candidates.append((best[0], best[1]))
        if len(files) > 1:
            skipped = [f[0] for f in files if f != best]
            print(f"  Dedup {base[:50]}: using {best[0][:60]}, skipped {skipped}", file=sys.stderr)

    print(f"Found {len(candidates)} unique papers from {sum(len(v) for v in groups.values())} files", file=sys.stderr)
    return candidates


def main():
    candidates = discover()

    all_spots = []
    for fn, path in candidates:
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  SKIP {fn}: {e}", file=sys.stderr)
            continue
        for rec in data:
            all_spots.append(flatten(rec))
        print(f"  {fn[:60]}...: {len(data)} spots", file=sys.stderr)

    by_sample = defaultdict(list)
    for s in all_spots:
        if s["sample_id"]:  # skip spots with no sample_id
            by_sample[s["sample_id"]].append(s)

    print(f"Total: {len(all_spots)} spots across {len(by_sample)} samples", file=sys.stderr)

    json.dump(all_spots, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
