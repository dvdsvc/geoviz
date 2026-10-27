"""
Load & normalize samples from geochron_pipeline_openai output.
Generates the same data as frontend/src/data/samples.ts.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

OUTPUT_DIR = os.environ.get(
    "PIPELINE_OUTPUT_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "geochron_pipeline_openai" / "output"),
)

PAPERS_JSON = os.environ.get(
    "PAPERS_JSON",
    str(Path(__file__).resolve().parent.parent / "scripts" / "papers.json"),
)

REGION_MAP = {
    "浙江": "华南", "福建": "华南", "Zhejiang": "华南", "Fujian": "华南",
    "eastern South China": "华南",
}


def _region_to_group(r: str) -> str:
    for k, v in REGION_MAP.items():
        if k in r:
            return v
    return "华南"


def _parse_gps(gps_str):
    if not gps_str:
        return 0, 0
    parts = gps_str.replace(" ", "").split(",")
    if len(parts) >= 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return 0, 0
    return 0, 0


def _parse_age(val) -> tuple[Optional[float], Optional[float]]:
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


def _pick(obj, *keys, default=""):
    for k in keys:
        if isinstance(obj, dict):
            v = obj.get(k)
            if v:
                if isinstance(v, dict):
                    return v.get("Selected_Term", v.get("value", str(v)))
                return v
        elif hasattr(obj, k):
            v = getattr(obj, k)
            if v:
                return str(v)
    return default


def load_papers() -> list[str]:
    if not os.path.exists(PAPERS_JSON):
        return []
    with open(PAPERS_JSON) as f:
        return json.load(f)


def load_samples(paper_name: str | None = None) -> list[dict]:
    """Load samples from pipeline output JSON files.

    If paper_name is None, loads all papers.
    Returns list of normalized sample dicts.
    """
    if paper_name:
        papers = [paper_name]
    else:
        papers = load_papers()

    all_samples: list[dict] = []

    for paper in papers:
        path = os.path.join(OUTPUT_DIR, f"{paper}_ages.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = json.load(f)

        for rec in data:
            sid = rec.get("sample_id", "")
            if not sid:
                continue

            age_val, age_err = _parse_age(rec.get("age_Ma") or rec.get("age_value"))
            rp = str(rec.get("Region_Province", ""))
            lat, lng = _parse_gps(rec.get("GPS", ""))

            sample = {
                "sampleId": sid,
                "region": _region_to_group(rp),
                "regionProvince": rp,
                "basin": str(rec.get("Basin", "")),
                "location": str(rec.get("Location", "")),
                "city": str(rec.get("City", "")),
                "specificLocation": str(rec.get("Specific_Location", "")),
                "gps": str(rec.get("GPS", "")),
                "lat": lat,
                "lng": lng,
                "group": str(rec.get("Group", "")),
                "formation": str(rec.get("Formation", "")),
                "memberDepth": str(rec.get("Member_Depth", "")),
                "rockType": str(_pick(rec, "Rock_type")),
                "datingMineral": str(_pick(rec, "Dating_mineral")),
                "datingSystem": str(_pick(rec, "Isotope_system")),
                "technique": str(_pick(rec, "Dating_Technique")),
                "ageMa": age_val,
                "error": age_err,
                "mswd": rec.get("MSWD"),
                "nGrains": rec.get("n"),
                "ageType": str(_pick(rec, "Statistical_Model")),
                "physicalMethod": str(_pick(rec, "Physical_Method")),
                "distributionState": str(_pick(rec, "Distribution_State")),
                "reference": paper,
                "remarks": "",
            }
            all_samples.append(sample)

    # Assign sequential IDs
    for i, s in enumerate(all_samples):
        s["id"] = str(i + 1)
        s["dataId"] = f"D{i + 1:03d}"

    return all_samples


def sample_to_text(s: dict) -> str:
    """Convert a sample to a natural-language text for embedding."""
    parts = [f"样品 {s['sampleId']}"]
    if s["region"]:
        parts.append(f"位于{s['region']}")
    if s["regionProvince"]:
        parts.append(s["regionProvince"])
    if s["basin"]:
        parts.append(f"{s['basin']}盆地" if "盆地" not in s["basin"] else s["basin"])
    if s["formation"]:
        parts.append(f"{s['formation']}组" if "组" not in s["formation"] and "Formation" not in s["formation"] else s["formation"])
    if s["rockType"]:
        parts.append(f"岩性为{s['rockType']}")
    if s["ageMa"] is not None:
        err_str = f"±{s['error']}Ma" if s["error"] is not None else ""
        parts.append(f"年龄{s['ageMa']}{err_str}Ma" if err_str else f"年龄{s['ageMa']}Ma")
    if s["datingSystem"]:
        parts.append(f"{s['datingSystem']}定年")
    if s["technique"]:
        parts.append(f"采用{s['technique']}技术")
    if s["reference"]:
        parts.append(f"参考：{s['reference']}")
    return "，".join(parts)


if __name__ == "__main__":
    samples = load_samples()
    print(f"Loaded {len(samples)} samples from {len(load_papers())} papers")
    if samples:
        print(f"\nExample text:\n{sample_to_text(samples[0])}")
