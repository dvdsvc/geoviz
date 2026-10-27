"""
Convert geochron_pipeline_v3 batch Excel output to geo-viz compatible formats:
- *_ages.json (per paper, for sample_loader.py)
- spots.csv (merged all papers, for /api/spots)
"""

import json
import os
import sys
from pathlib import Path

import openpyxl

BATCH_DIR = sys.argv[1] if len(sys.argv) > 1 else (
    'data/private/extraction_batch'
)
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else (
    'data/private/pipeline_output'
)
SPOTS_CSV_OUT = os.path.join(OUT_DIR, "spots.csv")

os.makedirs(OUT_DIR, exist_ok=True)

AGE_SAMPLE_COLS = [
    "sample_id", "internal_id", "age_Ma_raw", "age_value", "error_1sigma",
    "Dating_mineral", "Dating_mineral_reasoning", "Dating_mineral_source",
    "Isotope_system", "Isotope_system_reasoning", "Isotope_system_source",
    "Dating_Technique", "Dating_Technique_reasoning", "Dating_Technique_source",
    "Age_Interpretation", "Age_Interpretation_reasoning", "Age_Interpretation_source",
    "Physical_Method", "Physical_Method_reasoning", "Physical_Method_source",
    "Statistical_Model", "Statistical_Model_reasoning", "Statistical_Model_source",
    "Distribution_State", "Distribution_State_reasoning", "Distribution_State_source",
    "Error_Scale_Sourcing", "Error_Scale_Sourcing_reasoning", "Error_Scale_Sourcing_source",
    "MSWD", "n", "Is_Primary",
    "Rock_type", "Rock_type_EN", "Rock_type_SKOS", "Rock_type_hierarchy",
    "Formation", "Group", "Member_Depth",
    "Location", "Region_Province", "City", "Specific_Location", "GPS", "Basin",
    "source_context",
]

SPOT_COLS = [
    "spot_id", "sample_id",
    "u_ppm", "th_ppm", "th_u_ratio",
    "r206_238_val", "r206_238_err",
    "r207_235_val", "r207_235_err",
    "r207_206_val", "r207_206_err",
    "age_206_238_val", "age_206_238_err",
    "age_207_235_val", "age_207_235_err",
    "concordance",
]


def excel_to_ages_json(xlsx_path: str, paper_name: str):
    """Extract age_sample_data sheet and save as _ages.json."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "age_sample_data" not in wb.sheetnames:
        print(f"  SKIP {paper_name}: no age_sample_data sheet")
        return []

    ws = wb["age_sample_data"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))  # skip header
    records = []
    for row in rows:
        rec = {}
        for i, col_name in enumerate(AGE_SAMPLE_COLS):
            val = row[i] if i < len(row) else None
            # Normalize None
            if val is None:
                val = ""
            rec[col_name] = val
        # Build age_Ma in format sample_loader._parse_age expects: "142.58±0.61Ma"
        raw = str(rec.get("age_Ma_raw", ""))
        if "±" in raw or "+" in raw:
            rec["age_Ma"] = raw.replace(" ", "")
        else:
            age_val = rec.get("age_value", "")
            err_val = rec.get("error_1sigma", "")
            if err_val not in ("", None, 0):
                rec["age_Ma"] = f"{age_val}±{err_val}Ma"
            else:
                rec["age_Ma"] = f"{age_val}Ma"
        records.append(rec)

    wb.close()

    json_path = os.path.join(OUT_DIR, f"{paper_name}_ages.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return records


def excel_to_spot_rows(xlsx_path: str):
    """Extract spot_data sheet rows."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    if "spot_data" not in wb.sheetnames:
        print(f"  SKIP spots: no spot_data sheet")
        return []

    ws = wb["spot_data"]
    # Read header
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = {}
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else None
            rec[h] = val if val is not None else ""
        rows.append(rec)

    wb.close()
    return rows


def main():
    batch_dir = Path(BATCH_DIR)
    xlsx_files = sorted(batch_dir.glob("*.xlsx"))
    print(f"Found {len(xlsx_files)} Excel files in {batch_dir}")

    total_samples = 0
    total_spots = 0
    papers_list = []

    for xf in xlsx_files:
        paper_name = xf.stem.split("__")[0]  # Use the paper key as name
        print(f"\nProcessing: {xf.name} -> {paper_name}")

        records = excel_to_ages_json(str(xf), paper_name)
        total_samples += len(records)
        papers_list.append(paper_name)

    # Merge all papers list
    papers_json_path = os.path.join(os.path.dirname(OUT_DIR), "scripts", "papers.json")
    os.makedirs(os.path.dirname(papers_json_path), exist_ok=True)
    with open(papers_json_path, "w", encoding="utf-8") as f:
        json.dump(papers_list, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(papers_list)} papers to {papers_json_path}")

    # Merge all spot data into spots.csv
    import csv
    all_spot_rows = []
    for xf in xlsx_files:
        rows = excel_to_spot_rows(str(xf))
        if rows:
            all_spot_rows.extend(rows)
            print(f"  {xf.name}: {len(rows)} spots")

    if all_spot_rows:
        # Collect all column names
        all_cols = ["sample_id", "spot_id", "s_discarded"] + SPOT_COLS[2:]
        with open(SPOTS_CSV_OUT, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_cols, extrasaction="ignore")
            writer.writeheader()
            for row in all_spot_rows:
                row["s_discarded"] = False
                writer.writerow(row)
        total_spots = len(all_spot_rows)
        print(f"\nSaved {total_spots} spots to {SPOTS_CSV_OUT}")

    print(f"\nDone: {total_samples} samples from {len(papers_list)} papers, {total_spots} spots")
    print(f"Output dir: {OUT_DIR}")
    print(f"\nNext: Set env PIPELINE_OUTPUT_DIR={OUT_DIR} and restart backend")


if __name__ == "__main__":
    main()
