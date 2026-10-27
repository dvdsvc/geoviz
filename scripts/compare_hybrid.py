#!/usr/bin/env python3
"""
Compare pure LCS (existing provenance.json) vs hybrid (str.find + LCS window).
Only runs hybrid — reads existing LCS results from disk.
"""

import json, sys, re, math, time
from pathlib import Path

import fitz

sys.path.insert(0, 'integrations/private/extraction')
from provenance_mapper import (
    normalize, ngrams, _best_lcs_spans, _accept_lcs_match, find_in_page, keyword_match,
)

PIPELINE_OUTPUT = Path('data/private/pipeline')
WINDOW_CHARS = 500


def collapse_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def find_in_page_hybrid(page, ctx_norm: str, coverage: float = 0.4, density: float = 0.2):
    words = page.get_text("words")
    if not words or len(ctx_norm) < 8:
        return None, None, None

    raw_chars = []
    norm_chars = []
    char_to_word = []
    for wi, w in enumerate(words):
        w_text = w[4]
        w_norm = normalize(w_text)
        for ci in range(len(w_norm)):
            raw_chars.append(w_text[min(ci, len(w_text) - 1)])
            norm_chars.append(w_norm[ci])
            char_to_word.append(wi)
    page_norm = "".join(norm_chars)
    page_raw = "".join(raw_chars)

    # Build collapsed version for str.find
    collapsed_chars = []
    collapsed_to_norm = []
    last_was_space = False
    for i, c in enumerate(norm_chars):
        ws = c in (' ', '\n', '\r', '\t')
        if ws:
            if not last_was_space:
                collapsed_chars.append(' ')
                collapsed_to_norm.append(i)
                last_was_space = True
        else:
            collapsed_chars.append(c)
            collapsed_to_norm.append(i)
            last_was_space = False

    page_collapsed = "".join(collapsed_chars)
    ctx_collapsed = collapse_ws(ctx_norm)

    # Find candidates with str.find
    candidates = []
    pos = 0
    while True:
        idx = page_collapsed.find(ctx_collapsed, pos)
        if idx == -1:
            break
        candidates.append((idx, idx + len(ctx_collapsed)))
        pos = idx + 1

    # Also try no-space version
    ctx_nosp = ctx_norm.replace(" ", "")
    if ctx_nosp != ctx_collapsed:
        pos = 0
        while True:
            idx = page_collapsed.find(ctx_nosp, pos)
            if idx == -1:
                break
            candidates.append((idx, idx + len(ctx_nosp)))
            pos = idx + 1

    best_bbox, best_matched, best_method = None, None, None

    if candidates:
        for c_start, c_end in candidates:
            if c_start >= len(collapsed_to_norm) or c_end - 1 >= len(collapsed_to_norm):
                continue
            norm_start = collapsed_to_norm[c_start]
            norm_end = collapsed_to_norm[min(c_end - 1, len(collapsed_to_norm) - 1)] + 1

            win_start = max(0, norm_start - WINDOW_CHARS)
            win_end = min(len(page_norm), norm_end + WINDOW_CHARS)

            win_tokens = ngrams(page_norm[win_start:win_end], 3)
            ctx_tokens = ngrams(ctx_norm, 3)

            if len(ctx_tokens) < 5 or len(win_tokens) < len(ctx_tokens):
                continue

            spans = _best_lcs_spans(win_tokens, ctx_tokens)
            if not spans:
                continue

            accepted = None
            for k in sorted(spans.keys(), reverse=True):
                if _accept_lcs_match(spans[k], len(ctx_tokens), coverage, density):
                    accepted = spans[k]
                    break
            if accepted is None:
                for k in sorted(spans.keys(), reverse=True):
                    if _accept_lcs_match(spans[k], len(ctx_tokens), coverage * 0.6, density * 0.5):
                        accepted = spans[k]
                        break
            if accepted is None:
                continue

            char_start = win_start + accepted.start
            char_end = min(win_start + accepted.end + 2, len(page_raw) - 1)

            sw = char_to_word[char_start] if char_start < len(char_to_word) else 0
            ew = char_to_word[min(char_end, len(char_to_word) - 1)]

            bboxes = [words[i][:4] for i in range(sw, ew + 1)]
            union = (min(b[0] for b in bboxes), min(b[1] for b in bboxes),
                     max(b[2] for b in bboxes), max(b[3] for b in bboxes))
            matched = page_raw[char_start:char_end + 1]

            if best_matched is None or len(matched) > len(best_matched):
                best_bbox, best_matched, best_method = union, matched, "hybrid"

    if best_bbox:
        return best_bbox, best_matched, best_method

    return find_in_page(page, ctx_norm, coverage, density)


def find_in_pdf_hybrid(doc, context: str, record_id: str = ""):
    if not context or len(context.strip()) < 5:
        return None, None, None, "too_short"

    ctx_norm = normalize(context)

    kw_result = keyword_match(doc, context, record_id)
    if kw_result:
        return kw_result

    ctx_set = set(ngrams(ctx_norm, 3))
    candidate_pages = []
    for pi in range(doc.page_count):
        page_text = doc[pi].get_text("text")
        overlap = ctx_set & set(ngrams(normalize(page_text), 3))
        qc = len(overlap) / max(len(ctx_set), 1)
        if qc >= 0.3:
            candidate_pages.append((pi, qc))
    candidate_pages.sort(key=lambda x: -x[1])

    best_page, best_bbox, best_matched, best_method, best_len = None, None, None, None, 0

    for pi, _ in candidate_pages:
        bbox, matched, method = find_in_page_hybrid(doc[pi], ctx_norm)
        if bbox and matched and len(matched) > best_len:
            best_len = len(matched)
            best_page, best_bbox, best_matched, best_method = pi + 1, bbox, matched, method
            if method == "hybrid" and best_len >= 15:
                break

    if best_page and best_len < 10:
        for pi in range(doc.page_count):
            bbox, matched, method = find_in_page_hybrid(doc[pi], ctx_norm, 0.25, 0.1)
            if bbox and matched and len(matched) > best_len:
                best_len = len(matched)
                best_page, best_bbox, best_matched = pi + 1, bbox, matched
                best_method = method + "_loose"

    if best_page:
        return (best_page, best_bbox, best_matched, f"page_{best_method}")
    return None, None, None, "not_found"


def map_hybrid(doc, records: list, data_type: str) -> list:
    """Same field logic as provenance_mapper.map_provenance, using hybrid search."""
    results = []
    cv_dims = [
        "Dating_mineral", "Isotope_system", "Dating_Technique",
        "Age_Interpretation", "Physical_Method", "Statistical_Model",
        "Distribution_State", "Error_Scale_Sourcing",
    ]
    scalar_dims = [
        ("age_value", "Age (Ma)"), ("error_1s", "Error (1σ)"),
        ("MSWD", "MSWD"), ("n", "n"), ("Is_Primary", "Is Primary"),
        ("Rock_type", "Rock Type"), ("Formation", "Formation"),
        ("Group", "Group"), ("Member_Depth", "Member / Depth"),
        ("Location", "Location"), ("Region_Province", "Region / Province"),
        ("City", "City"), ("Specific_Location", "Specific Location"),
        ("GPS", "GPS"), ("Basin", "Basin"),
    ]

    for ri, rec in enumerate(records):
        rec_id = rec.get("spot_id") or rec.get("sample_id") or str(ri)

        entries = []
        if rec.get("source_context"):
            entries.append({
                "label": "Age Context",
                "display": rec.get("age_Ma", ""),
                "search_texts": [rec["source_context"]],
            })
        if rec.get("context"):
            entries.append({
                "label": "Context", "display": rec_id,
                "search_texts": [rec["context"]],
            })
        for dim in cv_dims:
            obj = rec.get(dim)
            if not isinstance(obj, dict):
                continue
            term = (obj.get("Selected_Term") or "")
            if term == "None":
                term = ""
            st = []
            if obj.get("Source_Context"):
                st.append(obj["Source_Context"])
            if obj.get("evidence"):
                st.append(obj["evidence"])
            if st:
                entries.append({"label": dim, "display": term, "search_texts": st})
        for fk, fl in scalar_dims:
            val = rec.get(fk)
            if val is None or val == "" or val is False:
                continue
            if fk == "Is_Primary" and not val:
                continue
            vs = str(val)
            if not vs.strip():
                continue
            st = []
            if len(vs) >= 6 and not vs.replace(".", "").replace("-", "").isdigit():
                st = [vs]
            entries.append({"label": fl, "display": vs, "search_texts": st})

        for entry in entries:
            page, bbox, matched, mtype = None, None, None, "not_found"
            for st in entry["search_texts"]:
                if not st or len(st.strip()) < 3:
                    continue
                page, bbox, matched, mtype = find_in_pdf_hybrid(doc, st, record_id=rec_id)
                if page:
                    break
            results.append({
                "data_type": data_type, "record_id": rec_id,
                "label": entry["label"], "display": entry["display"],
                "page": page, "bbox": list(bbox) if bbox else None,
                "matched_text": matched, "match_type": mtype,
            })
    return results


def main():
    from provenance_v3 import excel_to_records, find_pdf

    paper_key = sys.argv[1] if len(sys.argv) > 1 else "liu2016"
    v3_batch = Path('data/private/extraction_batch')

    # Find xlsx
    xlsx_path = None
    for f in v3_batch.iterdir():
        if f.suffix == ".xlsx" and f.stem.startswith(f"{paper_key}__"):
            xlsx_path = f
            break
    stem = xlsx_path.stem
    chinese_name = stem.split("__", 1)[1]

    # Find existing provenance.json as baseline
    existing = sorted(
        [p for p in PIPELINE_OUTPUT.glob("*_provenance.json") if chinese_name[:20] in p.stem],
        key=lambda x: x.stat().st_mtime, reverse=True
    )
    if not existing:
        print("No existing provenance.json found")
        return
    lcs_data = json.load(open(existing[0]))

    print(f"Paper: {paper_key} → {chinese_name[:60]}")
    print(f"Baseline: {existing[0].name}")
    print(f"  LCS fields={lcs_data['total_fields']}, found={lcs_data['found_count']}")

    # Load records
    records = excel_to_records(xlsx_path)
    ages = records.get("ages", [])
    print(f"Records: {len(ages)} ages")

    # Open PDF
    pdf_path = find_pdf(paper_key)
    doc = fitz.open(str(pdf_path))
    max_pages = min(doc.page_count, 15)
    doc.select(list(range(max_pages)))

    # Run hybrid only
    print("\nRunning HYBRID (str.find + LCS window)...")
    t0 = time.time()
    hybrid_results = map_hybrid(doc, ages, "age")
    elapsed = time.time() - t0

    hybrid_found = sum(1 for p in hybrid_results if p["page"] is not None)
    lcs_results = lcs_data["provenances"]
    lcs_found = sum(1 for p in lcs_results if p["page"] is not None)

    print(f"  Hybrid: {elapsed:.1f}s, Found: {hybrid_found}/{len(hybrid_results)}")
    print(f"  LCS:    {lcs_found}/{len(lcs_results)} (from disk)")

    # Compare field-by-field
    if len(hybrid_results) != len(lcs_results):
        print(f"\n  WARNING: field counts differ! hybrid={len(hybrid_results)} lcs={len(lcs_results)}")

    agree = page_diff = hybrid_only = lcs_only = both_miss = 0
    n = min(len(hybrid_results), len(lcs_results))

    for i in range(n):
        h, l = hybrid_results[i], lcs_results[i]
        hf, lf = h["page"] is not None, l["page"] is not None
        if hf and lf:
            if h["page"] == l["page"]:
                agree += 1
            else:
                page_diff += 1
        elif hf and not lf:
            hybrid_only += 1
        elif lf and not hf:
            lcs_only += 1
        else:
            both_miss += 1

    print(f"\n{'='*60}")
    print(f"  Both found, same page: {agree}")
    print(f"  Both found, diff page: {page_diff}")
    print(f"  Hybrid only:           {hybrid_only}")
    print(f"  LCS only:              {lcs_only}")
    print(f"  Both miss:             {both_miss}")

    if lcs_only > 0:
        print(f"\n  LCS found but hybrid missed:")
        for i in range(n):
            h, l = hybrid_results[i], lcs_results[i]
            if l["page"] and not h["page"]:
                print(f"    [{i}] {l['label']:25s} | {l['display'][:50]} | LCS page={l['page']}")

    if hybrid_only > 0:
        print(f"\n  Hybrid found but LCS missed:")
        for i in range(n):
            h, l = hybrid_results[i], lcs_results[i]
            if h["page"] and not l["page"]:
                print(f"    [{i}] {h['label']:25s} | {h['display'][:50]} | hybrid page={h['page']}")

    doc.close()


if __name__ == "__main__":
    main()
