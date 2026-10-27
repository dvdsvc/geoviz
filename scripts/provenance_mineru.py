#!/usr/bin/env python3
"""
Provenance mapper: reuse existing matching logic, but search MinerU layout.json
spans instead of PyMuPDF page text.

MinerU spans → PyMuPDF word format → same keyword_match + lcs_fuzzy_align → provenance.json
"""

import json, sys, os, re, math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from typing import NamedTuple, Optional

import fitz  # only for page dimensions + rendering

PDF_ROOT = Path('data/private/papers')
MINERU_ROOT = Path('data/private/MinerU')
PIPELINE_OUTPUT = Path('data/private/pipeline')
OUTPUT_DIR = PIPELINE_OUTPUT


# ============================================================
# Copied from provenance_mapper.py (text normalize + matching)
# ============================================================

def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.replace(" ", "").replace("　", "").replace("\n", "").replace("\r", "")
    result = []
    for c in s:
        code = ord(c)
        if 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        elif code == 0xFF0E:
            result.append(".")
        else:
            result.append(c)
    return "".join(result)


def ngrams(s: str, n: int = 3) -> list:
    return [s[i:i + n] for i in range(max(0, len(s) - n + 1))]


class LcsSpan(NamedTuple):
    matches: int
    start: int
    end: int

    @property
    def span_len(self) -> int:
        return 0 if self.start < 0 else self.end - self.start + 1


def _best_lcs_spans(source: list, extraction: list) -> dict:
    n = len(source)
    m = len(extraction)
    if n == 0 or m == 0:
        return {}

    prev_row = [[-1] * (m + 1) for _ in range(m + 1)]
    curr_row = [[-1] * (m + 1) for _ in range(m + 1)]
    for j in range(m + 1):
        prev_row[j][0] = 0

    best_per_k = {}

    for i in range(1, n + 1):
        src_tok = source[i - 1]
        curr_row[0][0] = i
        for k in range(1, m + 1):
            curr_row[0][k] = -1

        for j in range(1, m + 1):
            curr_row[j][0] = i
            matches_here = src_tok == extraction[j - 1]
            for k in range(1, m + 1):
                skip_source = prev_row[j][k]
                skip_extraction = curr_row[j - 1][k]
                best = skip_source if skip_source > skip_extraction else skip_extraction
                if matches_here:
                    match_cand = i - 1 if k == 1 else prev_row[j - 1][k - 1]
                    best = max(best, match_cand)
                curr_row[j][k] = best

        end = i - 1
        for k in range(1, m + 1):
            s = curr_row[m][k]
            if s < 0:
                continue
            existing = best_per_k.get(k)
            if existing is None:
                best_per_k[k] = LcsSpan(matches=k, start=s, end=end)
                continue
            new_len = end - s + 1
            cur_len = existing.span_len
            if new_len < cur_len or (new_len == cur_len and s < existing.start):
                best_per_k[k] = LcsSpan(matches=k, start=s, end=end)

        prev_row, curr_row = curr_row, prev_row

    return best_per_k


def _accept_lcs_match(span: LcsSpan, extraction_len: int,
                      coverage_threshold: float = 0.4,
                      density_threshold: float = 0.2) -> bool:
    if span.matches == 0 or extraction_len == 0:
        return False
    needed = math.ceil(extraction_len * coverage_threshold)
    if span.span_len <= 0:
        return False
    density = span.matches / span.span_len
    return span.matches >= needed and density >= density_threshold


def lcs_fuzzy_align(ctx_tokens: list, page_tokens: list, page_raw: str,
                    char_to_word: list, words: list,
                    coverage_threshold: float = 0.4,
                    density_threshold: float = 0.2):
    if not ctx_tokens or not page_tokens:
        return None, None

    spans = _best_lcs_spans(page_tokens, ctx_tokens)
    if not spans:
        return None, None

    accepted = None
    for k in sorted(spans.keys(), reverse=True):
        candidate = spans[k]
        if _accept_lcs_match(candidate, len(ctx_tokens), coverage_threshold, density_threshold):
            accepted = candidate
            break

    if accepted is None:
        for k in sorted(spans.keys(), reverse=True):
            candidate = spans[k]
            if _accept_lcs_match(candidate, len(ctx_tokens),
                                 coverage_threshold * 0.6, density_threshold * 0.5):
                accepted = candidate
                break

    if accepted is None:
        return None, None

    char_start = accepted.start
    char_end = min(accepted.end + 2, len(page_raw) - 1)

    start_wi = char_to_word[char_start] if char_start < len(char_to_word) else 0
    end_wi = char_to_word[min(char_end, len(char_to_word) - 1)]

    bboxes = [words[i][:4] for i in range(start_wi, end_wi + 1)]
    union = (
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        max(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
    )

    matched_text = page_raw[char_start:char_end + 1]
    return union, matched_text


def extract_keywords(text: str) -> list:
    keys = []
    for m in re.finditer(r"[A-Z]{2,}-\d+(?:-\d+)?[A-Z]*", text):
        keys.append(m.group())
    for m in re.finditer(r"\d+\.?\d*\s*[±±]\s*\d+\.?\d*", text):
        keys.append(m.group().replace(" ", ""))
    for m in re.finditer(r"[“\"]([^”\"]+)[”\"]", text):
        keys.append(m.group(1))
    seen = set()
    result = []
    for k in keys:
        if k not in seen and len(k) >= 3:
            seen.add(k)
            result.append(k)
    result.sort(key=len, reverse=True)
    return result


# ============================================================
# MinerU span → PyMuPDF word format adapter
# ============================================================

def mineru_spans_to_words(spans: list[dict]) -> list:
    """Convert MinerU spans to PyMuPDF get_text('words') format.
    Format: [x0, y0, x1, y1, text, block_no, line_no, word_no]
    """
    words = []
    for i, span in enumerate(spans):
        bbox = span["bbox"]
        if len(bbox) >= 4:
            words.append([bbox[0], bbox[1], bbox[2], bbox[3], span["text"], i, 0, 0])
    return words


def find_in_page_words(words: list, ctx_norm: str, coverage: float = 0.4, density: float = 0.2):
    """Same as provenance_mapper.find_in_page but takes words list instead of page object."""
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

    ctx_tokens = ngrams(ctx_norm, 3)
    page_tokens = ngrams(page_norm, 3)

    if len(ctx_tokens) >= 5 and len(page_tokens) >= len(ctx_tokens):
        bbox, matched = lcs_fuzzy_align(ctx_tokens, page_tokens, page_raw,
                                        char_to_word, words, coverage, density)
        if bbox and matched:
            return bbox, matched, "lcs_fuzzy"

    sm = SequenceMatcher(None, ctx_norm, page_norm)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 10]
    if not blocks:
        blocks = [b for b in sm.get_matching_blocks() if b.size >= 6]

    if blocks:
        blocks.sort(key=lambda x: -x.size)
        best = blocks[0]
        char_start = best.b
        char_end = best.b + best.size - 1

        start_wi = char_to_word[char_start] if char_start < len(char_to_word) else 0
        end_wi = char_to_word[min(char_end, len(char_to_word) - 1)]

        bboxes = [words[i][:4] for i in range(start_wi, end_wi + 1)]
        union = (min(b[0] for b in bboxes), min(b[1] for b in bboxes),
                 max(b[2] for b in bboxes), max(b[3] for b in bboxes))
        matched = page_raw[char_start:char_end + 1]
        return union, matched, "lcs_substr"

    return None, None, None


def keyword_match_pages(page_words_list: list[list], context: str, record_id: str):
    """Same as provenance_mapper.keyword_match but searches MinerU words."""
    keywords = []
    if record_id and re.match(r"^[A-Z]{2,}-\d+-\d+", record_id):
        keywords.append(record_id)
    keywords.extend(extract_keywords(context))

    for kw in keywords:
        if re.match(r"^\d+$", kw) or len(kw) < 6:
            continue
        hit_pages = []
        for pi, words in enumerate(page_words_list):
            areas = []
            for w in words:
                if kw in w[4]:  # w[4] = text
                    areas.append(tuple(w[:4]))
            if areas:
                hit_pages.append((pi + 1, areas))
        total = sum(len(a) for _, a in hit_pages)
        if total == 0:
            continue
        if total == 1 or (len(hit_pages) == 1 and total <= 3):
            pg, areas = hit_pages[0]
            return (pg, areas[0], kw, "keyword_exact")
    return None


def find_in_pdf_words(page_words_list: list[list], context: str, record_id: str = ""):
    """Same as provenance_mapper.find_in_pdf but on MinerU word lists."""
    if not context or len(context.strip()) < 5:
        return None, None, None, "too_short"

    ctx_norm = normalize(context)

    kw_result = keyword_match_pages(page_words_list, context, record_id)
    if kw_result:
        return kw_result

    ctx_tokens = ngrams(ctx_norm, 3)
    ctx_set = set(ctx_tokens)
    candidate_pages = []

    for pi, words in enumerate(page_words_list):
        all_text = " ".join(w[4] for w in words)
        page_norm = normalize(all_text)
        page_grams = ngrams(page_norm, 3)
        overlap = ctx_set & set(page_grams)
        quick_coverage = len(overlap) / max(len(ctx_set), 1)
        if quick_coverage >= 0.3:
            candidate_pages.append((pi, quick_coverage))

    candidate_pages.sort(key=lambda x: -x[1])

    best_page = None
    best_bbox = None
    best_matched = None
    best_method = None
    best_len = 0

    for pi, _ in candidate_pages:
        bbox, matched, method = find_in_page_words(page_words_list[pi], ctx_norm)
        if bbox and matched:
            matched_len = len(matched)
            if matched_len > best_len:
                best_len = matched_len
                best_page = pi + 1
                best_bbox = bbox
                best_matched = matched
                best_method = method
            if method == "lcs_fuzzy" and matched_len >= 15:
                break

    if best_page:
        if best_len < 10:
            for pi in range(len(page_words_list)):
                bbox, matched, method = find_in_page_words(page_words_list[pi], ctx_norm, 0.25, 0.1)
                if bbox and matched and len(matched) > best_len:
                    best_len = len(matched)
                    best_page = pi + 1
                    best_bbox = bbox
                    best_matched = matched
                    best_method = method + "_loose"

    if best_page:
        return (best_page, best_bbox, best_matched, f"page_{best_method}")

    return None, None, None, "not_found"


# ============================================================
# Provenance mapping (copied from provenance_mapper.map_provenance)
# ============================================================

def map_provenance(page_words_list: list[list], records: list, data_type: str) -> list:
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

    results = []
    for ri, rec in enumerate(records):
        rec_id = rec.get("spot_id") or rec.get("sample_id") or str(ri)
        if data_type == "spot" and rec.get("sample_id"):
            sid = rec.get("spot_id", "")
            if not sid or not str(sid).startswith(str(rec["sample_id"])):
                rec_id = f"{rec['sample_id']}-{sid}" if sid else rec["sample_id"]

        entries = []

        if rec.get("source_context"):
            entries.append({"label": "Age Context", "display": str(rec.get("age_Ma", "")),
                           "search_texts": [rec["source_context"]]})
        if rec.get("context"):
            entries.append({"label": "Context", "display": rec_id,
                           "search_texts": [rec["context"]]})

        for dim in cv_dims:
            obj = rec.get(dim)
            if not isinstance(obj, dict):
                continue
            term = obj.get("Selected_Term") or ""
            if term == "None" or term is None:
                term = ""
            search_texts = []
            if obj.get("Source_Context"):
                search_texts.append(obj["Source_Context"])
            if obj.get("evidence"):
                search_texts.append(obj["evidence"])
            if not search_texts:
                continue
            entries.append({"label": dim, "display": term, "search_texts": search_texts})

        for field_key, field_label in scalar_dims:
            val = rec.get(field_key)
            if val is None or val == "" or val is False:
                continue
            if field_key == "Is_Primary" and not val:
                continue
            val_str = str(val)
            if not val_str.strip():
                continue
            search_texts = []
            if len(val_str) >= 6 and not val_str.replace(".", "").replace("-", "").isdigit():
                search_texts = [val_str]
            entries.append({"label": field_label, "display": val_str, "search_texts": search_texts})

        for entry in entries:
            page, bbox, matched, mtype = None, None, None, "not_found"
            for st in entry["search_texts"]:
                if not st or len(st.strip()) < 3:
                    continue
                page, bbox, matched, mtype = find_in_pdf_words(page_words_list, st, record_id=rec_id)
                if page:
                    break
            results.append({
                "data_type": data_type,
                "record_id": rec_id,
                "label": entry["label"],
                "display": entry["display"],
                "page": page,
                "bbox": list(bbox) if bbox else None,
                "matched_text": matched,
                "match_type": mtype,
            })

    return results


# ============================================================
# Main
# ============================================================

def load_mineru_spans(paper_name: str):
    """Load MinerU layout.json spans, organized by page."""
    for d in MINERU_ROOT.iterdir():
        if not d.is_dir():
            continue
        pdf_part = d.name.rsplit(".pdf-", 1)[0] + ".pdf"
        pdf_basename = pdf_part.rsplit(".pdf", 1)[0]
        if pdf_basename == paper_name:
            layout_path = d / "layout.json"
            if not layout_path.exists():
                return None
            with open(layout_path, encoding="utf-8") as f:
                layout = json.load(f)

            page_spans = defaultdict(list)
            for page_idx, page_data in enumerate(layout.get("pdf_info", [])):
                for block in page_data.get("preproc_blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            page_spans[page_idx].append({
                                "bbox": span["bbox"],
                                "text": span["content"],
                            })
            return dict(page_spans)
    return None


def find_pdf(paper_name: str) -> Optional[Path]:
    for pdf in PDF_ROOT.rglob("*.pdf"):
        if pdf.stem == paper_name:
            return pdf
    return None


def run_single(paper_name: str):
    # Find PDF
    pdf_path = find_pdf(paper_name)
    if not pdf_path:
        print(f"  ERROR: PDF not found for {paper_name}")
        return

    # Load MinerU spans
    page_spans = load_mineru_spans(paper_name)
    if not page_spans:
        print(f"  ERROR: No MinerU data for {paper_name}")
        return

    # Convert to PyMuPDF word format per page
    doc = fitz.open(str(pdf_path))
    page_words_list = []
    for pi in range(doc.page_count):
        spans = page_spans.get(pi, [])
        words = mineru_spans_to_words(spans)
        page_words_list.append(words)
    page_dims = [(doc[i].rect.width, doc[i].rect.height) for i in range(doc.page_count)]

    total_spans = sum(len(w) for w in page_words_list)
    print(f"  MinerU spans: {total_spans} across {len(page_words_list)} pages")

    # Load pipeline data
    collections = {}
    files_to_load = {
        "ages": f"{paper_name}_ages.json",
        "failed": f"{paper_name}_failed.json",
        "spots": f"{paper_name}_spots.json",
        "spot_ids": f"{paper_name}_spot_ids.json",
    }
    for name, fn in files_to_load.items():
        # Find latest timestamped version
        prefix = f"{paper_name}_"
        candidates = sorted(
            [f for f in OUTPUT_DIR.iterdir()
             if f.name.startswith(prefix) and f.name.endswith(f"_{name}.json")],
            key=lambda x: x.stat().st_mtime, reverse=True)
        if candidates:
            with open(candidates[0], encoding="utf-8") as f:
                collections[name] = json.load(f)
            print(f"  Loaded {name}: {len(collections[name])} records")
        else:
            print(f"  [skip] no {name} file")

    if not collections:
        print(f"  ERROR: No pipeline data for {paper_name}")
        doc.close()
        return

    # Map provenance
    all_provenances = []
    type_map = {"ages": "age", "failed": "failed_age", "spots": "spot", "spot_ids": "spot"}
    for key, recs in collections.items():
        if not isinstance(recs, list):
            continue
        data_type = type_map.get(key, key)
        print(f"  Mapping {key} ({len(recs)} records)...")
        all_provenances.extend(map_provenance(page_words_list, recs, data_type))

    found = sum(1 for p in all_provenances if p["page"] is not None)
    not_found = sum(1 for p in all_provenances if p["page"] is None)
    print(f"  Found: {found}/{len(all_provenances)} fields")

    # Normalize bbox
    for p in all_provenances:
        if p["page"] and p["bbox"] and p["page"] <= len(page_dims):
            pw, ph = page_dims[p["page"] - 1]
            b = p["bbox"]
            p["bbox_norm"] = [b[0] / pw, b[1] / ph, b[2] / pw, b[3] / ph]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{paper_name}_{timestamp}_provenance.json"

    # Include page_images from existing render
    # Find existing pages dir or use the one we rendered
    pages_dir = None
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name.startswith(paper_name) and d.name.endswith("_pages"):
            pages_dir = d
            break

    page_images = []
    if pages_dir:
        for img_file in sorted(pages_dir.iterdir()):
            if img_file.suffix == ".png":
                import re as _re
                m = _re.match(r"page_(\d+)\.png", img_file.name)
                if m:
                    from PIL import Image
                    img = Image.open(img_file)
                    page_images.append({
                        "page": int(m.group(1)),
                        "image": img_file.name,
                        "width": img.size[0],
                        "height": img.size[1],
                        "dpi": 300,
                    })

    result = {
        "paper_name": paper_name,
        "pdf_path": str(pdf_path),
        "total_pages": doc.page_count,
        "total_fields": len(all_provenances),
        "found_count": found,
        "not_found_count": not_found,
        "page_images": page_images,
        "provenances": all_provenances,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Output: {out_path}")

    doc.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python provenance_mineru.py <paper_name>")
        print("       python provenance_mineru.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Find papers with both MinerU data and pipeline output
        mineru_papers = set()
        for d in MINERU_ROOT.iterdir():
            if d.is_dir():
                pdf_part = d.name.rsplit(".pdf-", 1)[0] + ".pdf"
                basename = pdf_part.rsplit(".pdf", 1)[0]
                mineru_papers.add(basename)

        pipeline_papers = set()
        for f in OUTPUT_DIR.iterdir():
            if f.name.endswith("_ages.json"):
                name = f.name[:-len("_ages.json")]
                parts = name.rsplit("_", 2)
                if len(parts) >= 3 and len(parts[-2]) == 8 and parts[-2].isdigit():
                    pipeline_papers.add("_".join(parts[:-2]))
                else:
                    pipeline_papers.add(name)

        common = sorted(mineru_papers & pipeline_papers)
        print(f"MinerU papers: {len(mineru_papers)}")
        print(f"Pipeline papers: {len(pipeline_papers)}")
        print(f"To map: {len(common)}")
        print()

        for paper_name in common:
            print(f"[{paper_name}]")
            run_single(paper_name)
            print()
    else:
        run_single(sys.argv[1])


if __name__ == "__main__":
    main()
