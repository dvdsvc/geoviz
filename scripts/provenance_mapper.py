#!/usr/bin/env python3
"""
Provenance Mapper: 将提取数据的 Source_Context 定位到 PDF 原文的位置。

策略：
  1. 长/唯一关键词 → PyMuPDF search_for 精确匹配
  2. 短/模糊文本 → 移植自 Google LongExtract 的 _best_lcs_spans 算法
     (token 级 LCS DP + coverage 门控 + density 门控)

用法：
  python provenance_mapper.py <paper_name>
"""

import json, sys, os, re, math
from collections import Counter, deque
from pathlib import Path
from difflib import SequenceMatcher
from typing import NamedTuple

import fitz  # PyMuPDF


# ============================================================
# Text normalization
# ============================================================

def normalize(s: str) -> str:
    """去除空格/换行、全角ASCII转半角、统一标点。"""
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


# ============================================================
# Strategy 1: 长关键词精确匹配
# ============================================================

def extract_keywords(text: str) -> list:
    """从 context 中提取可用于精确搜索的关键词（>= 6 字符）。"""
    keys = []
    # 样品编号：ZC-xx-x, 128-xxZK 等
    for m in re.finditer(r"[A-Z]{2,}-\d+(?:-\d+)?[A-Z]*", text):
        keys.append(m.group())
    # 年龄：xxx.x ± x.x
    for m in re.finditer(r"\d+\.?\d*\s*[±±]\s*\d+\.?\d*", text):
        keys.append(m.group().replace(" ", ""))
    # 引号内的文本
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


def keyword_match(doc, context: str, record_id: str):
    """
    策略 1：精确关键词匹配。
    仅对复合 ID（如 ZC-10-3）、>= 6 字符且在 PDF 中出现 <= 3 次的关键词。
    """
    keywords = []
    if record_id and re.match(r"^[A-Z]{2,}-\d+-\d+", record_id):
        keywords.append(record_id)
    keywords.extend(extract_keywords(context))

    for kw in keywords:
        if re.match(r"^\d+$", kw) or len(kw) < 6:
            continue
        # 检查全文出现次数
        hit_pages = []
        for pi in range(doc.page_count):
            areas = doc[pi].search_for(kw)
            if areas:
                hit_pages.append((pi + 1, areas))
        total = sum(len(a) for _, a in hit_pages)
        if total == 0:
            continue
        if total == 1 or (len(hit_pages) == 1 and total <= 3):
            pg, areas = hit_pages[0]
            return (pg, tuple(areas[0]), kw, "keyword_exact")
    return None


# ============================================================
# Strategy 2: LongExtract LCS span 算法（移植）
# ============================================================

class LcsSpan(NamedTuple):
    matches: int
    start: int
    end: int

    @property
    def span_len(self) -> int:
        return 0 if self.start < 0 else self.end - self.start + 1


_NO_MATCH = LcsSpan(matches=0, start=-1, end=-1)


def _best_lcs_spans(source: list, extraction: list) -> dict:
    """
    移植自 LongExtract resolver.py:_best_lcs_spans。

    O(n * m^2) DP，对每个可达的 match count k (1..m)，
    返回 source 中包含 extraction 的 k 个 token（作为子序列）的最紧 span。

    核心：对于每个 (i, j, k)，跟踪最小的 source 起始位置 s
    使得 source[s..i) 包含 extraction[0..j) 的至少 k 个 token 作为子序列。
    """
    n = len(source)
    m = len(extraction)
    if n == 0 or m == 0:
        return {}

    # Rolling rows: prev_row[j][k] = span_start[i-1][j][k]
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
    """
    移植自 LongExtract resolver.py:_accept_lcs_match。

    Coverage gate: matches >= ceil(extraction_len * coverage_threshold)
    Density gate:  matches / span_len >= density_threshold
    """
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
    """
    移植自 LongExtract resolver.py:_lcs_fuzzy_align_extraction。

    对 context tokens 在 page tokens 上做 LCS DP，
    用 coverage + density 门控找到最紧匹配 span。
    返回 (bbox, matched_text) 或 (None, None)。
    """
    if not ctx_tokens or not page_tokens:
        return None, None

    spans = _best_lcs_spans(page_tokens, ctx_tokens)
    if not spans:
        return None, None

    # 从高 match count 到低，找第一个通过双门的 span
    accepted = None
    for k in sorted(spans.keys(), reverse=True):
        candidate = spans[k]
        if _accept_lcs_match(candidate, len(ctx_tokens),
                             coverage_threshold, density_threshold):
            accepted = candidate
            break

    if accepted is None:
        # 降阈值重试
        for k in sorted(spans.keys(), reverse=True):
            candidate = spans[k]
            if _accept_lcs_match(candidate, len(ctx_tokens),
                                 coverage_threshold * 0.6,
                                 density_threshold * 0.5):
                accepted = candidate
                break

    if accepted is None:
        return None, None

    # span 是 token 级别的，映射回字符位置
    # token = trigram，token i 对应字符位置 i
    char_start = accepted.start
    char_end = min(accepted.end + 2, len(page_raw) - 1)  # +2 for trigram width

    # 映射到 word
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


def ngrams(s: str, n: int = 3) -> list:
    return [s[i:i+n] for i in range(max(0, len(s) - n + 1))]


# ============================================================
# 页面级匹配
# ============================================================

def find_in_page(page, ctx_norm: str, coverage: float = 0.4, density: float = 0.2):
    """
    在单页上搜索 context 的最佳匹配。

    1. 如果 context 较长（>= 60 chars），做 trigram LCS fuzzy align
    2. 如果 context 较短，也做 LCS fuzzy align（用 trigram token）
    3. 实在不行回退到 difflib LCS 子串

    返回 (bbox, matched_text, method) 或 (None, None, None)
    """
    words = page.get_text("words")
    if not words:
        return None, None, None
    if len(ctx_norm) < 8:
        return None, None, None

    # 构建字符数组 + word 映射
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

    # Tokenize: character trigrams
    ctx_tokens = ngrams(ctx_norm, 3)
    page_tokens = ngrams(page_norm, 3)

    if len(ctx_tokens) >= 5 and len(page_tokens) >= len(ctx_tokens):
        bbox, matched = lcs_fuzzy_align(
            ctx_tokens, page_tokens, page_raw,
            char_to_word, words, coverage, density)
        if bbox and matched:
            return bbox, matched, "lcs_fuzzy"

    # 回退：difflib 最长公共子串
    sm = SequenceMatcher(None, ctx_norm, page_norm)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 10]
    if not blocks:
        # 再降门槛
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


# ============================================================
# 全文搜索
# ============================================================

def find_in_pdf(doc, context: str, record_id: str = ""):
    """
    在 PDF 全文搜索 context 的最佳匹配。

    策略 1 → 长关键词精确匹配
    策略 2 → LongExtract LCS fuzzy align
    """
    if not context or len(context.strip()) < 5:
        return None, None, None, "too_short"

    ctx_norm = normalize(context)

    # 策略 1：长关键词精确匹配
    kw_result = keyword_match(doc, context, record_id)
    if kw_result:
        return kw_result

    # 策略 2：LongExtract LCS fuzzy align 逐页搜索
    # 先预筛：只对 context trigram 覆盖足够高的页面跑 DP
    ctx_tokens = ngrams(ctx_norm, 3)
    ctx_set = set(ctx_tokens)
    candidate_pages = []

    for pi in range(doc.page_count):
        page_text = doc[pi].get_text("text")
        page_norm = normalize(page_text)
        # 快速计数：这个页面有多少 context trigram 出现过
        page_grams = ngrams(page_norm, 3)
        overlap = ctx_set & set(page_grams)
        quick_coverage = len(overlap) / max(len(ctx_set), 1)
        if quick_coverage >= 0.3:  # 至少 30% trigram 重叠才考虑
            candidate_pages.append((pi, quick_coverage))

    # 按覆盖率降序，高覆盖率优先
    candidate_pages.sort(key=lambda x: -x[1])

    best_page = None
    best_bbox = None
    best_matched = None
    best_method = None
    best_len = 0

    for pi, _ in candidate_pages:
        bbox, matched, method = find_in_page(doc[pi], ctx_norm)
        if bbox and matched:
            matched_len = len(matched)
            if matched_len > best_len:
                best_len = matched_len
                best_page = pi + 1
                best_bbox = bbox
                best_matched = matched
                best_method = method
            # 如果匹配质量足够高，提前终止
            if method == "lcs_fuzzy" and matched_len >= 15:
                break

    if best_page:
        # 如果最佳匹配太短（< 10 字符），降低阈值再试
        if best_len < 10:
            for pi in range(doc.page_count):
                bbox, matched, method = find_in_page(doc[pi], ctx_norm, 0.25, 0.1)
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
# 记录级出处映射
# ============================================================

def map_provenance(doc, records: list, data_type: str) -> list:
    """为一组记录映射出处。

    聚合策略：
      - 受控词表维度：合并 Source_Context + evidence 为搜索文本（优先 Source_Context），
        展示 term = Selected_Term
      - Scalar 字段（Rock_type, Formation, ...）：搜索文本 = 字段值自身
      - 搜索结果取最佳命中的 page/bbox
    """
    results = []

    # 受控词表维度定义
    cv_dims = [
        "Dating_mineral", "Isotope_system", "Dating_Technique",
        "Age_Interpretation", "Physical_Method", "Statistical_Model",
        "Distribution_State", "Error_Scale_Sourcing",
    ]

    # Scalar 维度：字段名 → 展示标签
    scalar_dims = [
        ("age_value", "Age (Ma)"),
        ("error_1s", "Error (1σ)"),
        ("MSWD", "MSWD"),
        ("n", "n"),
        ("Is_Primary", "Is Primary"),
        ("Rock_type", "Rock Type"),
        ("Formation", "Formation"),
        ("Group", "Group"),
        ("Member_Depth", "Member / Depth"),
        ("Location", "Location"),
        ("Region_Province", "Region / Province"),
        ("City", "City"),
        ("Specific_Location", "Specific Location"),
        ("GPS", "GPS"),
        ("Basin", "Basin"),
    ]

    for ri, rec in enumerate(records):
        rec_id = rec.get("spot_id") or rec.get("sample_id") or str(ri)
        if data_type == "spot" and rec.get("sample_id"):
            sid = rec.get("spot_id", "")
            if not sid or not str(sid).startswith(str(rec["sample_id"])):
                rec_id = f"{rec['sample_id']}-{sid}" if sid else rec["sample_id"]

        entries = []

        # 1. top-level source_context（直接字段）
        if rec.get("source_context"):
            entries.append({
                "label": "Age Context",
                "display": rec.get("age_Ma", ""),
                "search_texts": [rec["source_context"]],
            })
        if rec.get("context"):
            entries.append({
                "label": "Context",
                "display": rec_id,
                "search_texts": [rec["context"]],
            })

        # 2. 受控词表维度：合并 Source_Context(优先) + evidence 做搜索
        for dim in cv_dims:
            obj = rec.get(dim)
            if not isinstance(obj, dict):
                continue
            term = obj.get("Selected_Term") or ""
            if term == "None" or term is None:
                term = ""

            search_texts = []
            # 优先 Source_Context（最接近原文）
            if obj.get("Source_Context"):
                search_texts.append(obj["Source_Context"])
            # 补充 evidence（含多页引用，更完整）
            if obj.get("evidence"):
                search_texts.append(obj["evidence"])

            if not search_texts:
                continue

            entries.append({
                "label": dim,
                "display": term,
                "search_texts": search_texts,
            })

        # 3. Scalar 字段（>= 6 字符才尝试搜索定位，太短的值只展示不搜索）
        for field_key, field_label in scalar_dims:
            val = rec.get(field_key)
            if val is None or val == "" or val is False:
                continue
            if field_key == "Is_Primary" and not val:
                continue
            val_str = str(val)
            if not val_str.strip():
                continue
            # 值 >= 6 字符 AND 不是纯数字/布尔值 才尝试 PDF 搜索
            search_texts = []
            if len(val_str) >= 6 and not val_str.replace(".", "").replace("-", "").isdigit():
                search_texts = [val_str]
            entries.append({
                "label": field_label,
                "display": val_str,
                "search_texts": search_texts,
            })

        # 逐条定位
        for entry in entries:
            page, bbox, matched, mtype = None, None, None, "not_found"

            # 按优先级依次尝试各 search_text
            for st in entry["search_texts"]:
                if not st or len(st.strip()) < 3:
                    continue
                page, bbox, matched, mtype = find_in_pdf(doc, st, record_id=rec_id)
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

def main():
    if len(sys.argv) < 2:
        print("Usage: python provenance_mapper.py <paper_name>")
        sys.exit(1)

    paper_name = sys.argv[1]
    output_dir = Path(__file__).parent / "output"
    pdf_dir = Path('data/private/浙江年龄')

    files_to_load = {
        "ages": output_dir / f"{paper_name}_ages.json",
        "failed": output_dir / f"{paper_name}_failed.json",
        "spots": output_dir / f"{paper_name}_spots.json",
        "spot_ids": output_dir / f"{paper_name}_spot_ids.json",
    }

    collections = {}
    for name, path in files_to_load.items():
        if path.exists():
            with open(path) as f:
                collections[name] = json.load(f)
            print(f"Loaded {name}: {len(collections[name])} records")
        else:
            print(f"  [skip] {path} not found")

    pdf_path = None
    run_report_path = output_dir / f"{paper_name}_run_report.json"
    if run_report_path.exists():
        with open(run_report_path) as f:
            report = json.load(f)
            pdf_path = report.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        for f in pdf_dir.glob("*.pdf"):
            pdf_path = str(f)
            break
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"Pages: {doc.page_count}")

    all_provenances = []
    for key in ["ages", "failed", "spot_ids", "spots"]:
        if key in collections:
            print(f"Mapping {key}...")
            all_provenances.extend(map_provenance(doc, collections[key],
                                                  key.replace("failed", "failed_age").replace("ages", "age")))

    found = sum(1 for p in all_provenances if p["page"] is not None)
    not_found = sum(1 for p in all_provenances if p["page"] is None)
    print(f"\nTotal: {len(all_provenances)} fields")
    print(f"  Found: {found}")
    print(f"  Not found: {not_found}")

    # 归一化坐标
    for p in all_provenances:
        if p["page"] and p["bbox"]:
            page_rect = doc[p["page"] - 1].rect
            pw, ph = page_rect.width, page_rect.height
            bbox = p["bbox"]
            p["bbox_norm"] = [bbox[0]/pw, bbox[1]/ph, bbox[2]/pw, bbox[3]/ph]

    # 渲染页面为图片（PyMuPDF 能正确处理中文 Type1 字体，PDF.js 不行）
    pages_dir = output_dir / f"{paper_name}_pages"
    pages_dir.mkdir(exist_ok=True)
    dpi = 300
    page_images = []
    for pi in range(doc.page_count):
        pix = doc[pi].get_pixmap(dpi=dpi)
        img_name = f"page_{pi+1:02d}.png"
        img_path = pages_dir / img_name
        pix.save(str(img_path))  # PyMuPDF 内置 save，输出 PNG
        page_images.append({
            "page": pi + 1,
            "image": img_name,
            "width": pix.width,
            "height": pix.height,
            "dpi": dpi,
        })
    print(f"  Rendered {doc.page_count} pages to {pages_dir}")

    output_path = output_dir / f"{paper_name}_provenance.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "paper_name": paper_name,
            "pdf_path": pdf_path,
            "total_pages": doc.page_count,
            "total_fields": len(all_provenances),
            "found_count": found,
            "not_found_count": not_found,
            "page_images": page_images,
            "provenances": all_provenances,
        }, f, ensure_ascii=False, indent=2)
    print(f"Output: {output_path}")
    doc.close()


if __name__ == "__main__":
    main()
