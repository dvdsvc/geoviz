#!/usr/bin/env python3
"""Generate samples.ts from pipeline ages.json files."""

import json, os, sys, re

OUTPUT_DIR = 'data/private/pipeline'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, "papers.json")) as f:
    PAPERS = json.load(f)

REGION_MAP = {
    "浙江": "华南", "福建": "华南", "Zhejiang": "华南", "Fujian": "华南",
    "eastern South China": "华南",
}

def region_to_group(r: str) -> str:
    for k, v in REGION_MAP.items():
        if k in r:
            return v
    return "华南"

def parse_gps(gps_str):
    if not gps_str:
        return 0, 0
    parts = gps_str.replace(" ", "").split(",")
    if len(parts) >= 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return 0, 0
    return 0, 0

def parse_age(val):
    if val is None:
        return None, None
    s = str(val).replace(" ", "").replace("Ma", "")
    m = re.match(r"([\d.]+)±?([\d.]*)?", s)
    if m:
        age = float(m.group(1))
        err = float(m.group(2)) if m.group(2) else None
        return age, err
    m = re.match(r"([\d.]+)", s)
    if m:
        return float(m.group(1)), None
    return None, None

def extract_samples(paper_name):
    path = os.path.join(OUTPUT_DIR, f"{paper_name}_ages.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    samples = []
    for rec in data:
        sid = rec.get("sample_id", "")
        if not sid:
            continue
        age_val, age_err = parse_age(rec.get("age_Ma") or rec.get("age_value"))
        rp = rec.get("Region_Province", "")
        lat, lng = parse_gps(rec.get("GPS", ""))
        samples.append({
            "sampleId": sid,
            "region": region_to_group(rp),
            "regionProvince": rp or "",
            "basin": rec.get("Basin", ""),
            "location": rec.get("Location", ""),
            "city": rec.get("City", ""),
            "specificLocation": rec.get("Specific_Location", ""),
            "gps": rec.get("GPS", ""),
            "lat": lat, "lng": lng,
            "group": rec.get("Group", ""),
            "formation": rec.get("Formation", ""),
            "memberDepth": rec.get("Member_Depth", ""),
            "rockType": rec.get("Rock_type", ""),
            "datingMineral": rec.get("Dating_mineral", {}).get("Selected_Term", "") if isinstance(rec.get("Dating_mineral"), dict) else rec.get("Dating_mineral", ""),
            "datingSystem": rec.get("Isotope_system", {}).get("Selected_Term", "") if isinstance(rec.get("Isotope_system"), dict) else rec.get("Isotope_system", ""),
            "technique": rec.get("Dating_Technique", {}).get("Selected_Term", "") if isinstance(rec.get("Dating_Technique"), dict) else rec.get("Dating_Technique", ""),
            "ageMa": age_val,
            "error": age_err,
            "mswd": rec.get("MSWD"),
            "nGrains": rec.get("n"),
            "ageType": rec.get("Statistical_Model", {}).get("Selected_Term", "") if isinstance(rec.get("Statistical_Model"), dict) else rec.get("Statistical_Model", ""),
            "physicalMethod": rec.get("Physical_Method", {}).get("Selected_Term", "") if isinstance(rec.get("Physical_Method"), dict) else rec.get("Physical_Method", ""),
            "distributionState": rec.get("Distribution_State", {}).get("Selected_Term") if isinstance(rec.get("Distribution_State"), dict) else rec.get("Distribution_State", ""),
            "reference": paper_name,
            "remarks": "",
        })
    return samples

def main():
    all_samples = []
    for paper in PAPERS:
        samples = extract_samples(paper)
        all_samples.extend(samples)
        print(f"  {paper[:40]}...: {len(samples)} samples", file=sys.stderr)

    for i, s in enumerate(all_samples):
        s["id"] = str(i + 1)
        s["dataId"] = f"D{i+1:03d}"

    print(f"Total: {len(all_samples)} samples", file=sys.stderr)

    print('import { Sample } from "@/types";')
    print()
    print("export const samples: Sample[] = [")
    for s in all_samples:
        print(f"  {{")
        for k in ["id", "dataId", "region", "regionProvince", "basin", "location", "city",
                   "specificLocation", "gps", "lat", "lng", "group", "formation",
                   "memberDepth", "sampleId", "rockType", "datingMineral", "datingSystem",
                   "technique", "ageMa", "error", "mswd", "nGrains", "ageType",
                   "physicalMethod", "distributionState", "reference", "remarks"]:
            v = s.get(k)
            if v is None:
                print(f"    {k}: null,")
            elif isinstance(v, str):
                escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                print(f'    {k}: "{escaped}",')
            elif isinstance(v, float):
                print(f"    {k}: {v},")
            else:
                print(f"    {k}: {v},")
        print(f"  }},")
    print("];")

if __name__ == "__main__":
    main()
