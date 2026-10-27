#!/usr/bin/env python3
"""Batch render PDFs from 华南(1) to PNG pages, serial, skipping already-rendered."""

import sys
import os
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

PDF_ROOT = Path('data/private/papers')
OUTPUT_DIR = Path('data/private/pipeline')
DPI = 300


def find_existing_basenames(output_dir: Path) -> set[str]:
    """Find already-rendered paper basenames by scanning *_pages/ dirs."""
    rendered = set()
    for d in output_dir.iterdir():
        if d.is_dir() and d.name.endswith("_pages"):
            # Strip _YYYYMMDD_HHMMSS_pages suffix to get base name
            # e.g., "He et al,2013_20260517_225149_pages" → "He et al,2013"
            name = d.name[:-len("_pages")]
            # Try to strip timestamp: last _\d{8}_\d{6} segment
            parts = name.rsplit("_", 2)
            if len(parts) >= 3:
                candidate = "_".join(parts[:-2])
                # Validate it looks like a timestamp pattern
                if len(parts[-2]) == 8 and parts[-2].isdigit() and len(parts[-1]) == 6 and parts[-1].isdigit():
                    rendered.add(candidate)
                    continue
            rendered.add(name)
    return rendered


def collect_pdfs(root: Path) -> list[Path]:
    """Recursively collect all PDFs."""
    pdfs = []
    for pdf in sorted(root.rglob("*.pdf")):
        # Skip hidden files and macOS resource forks
        if pdf.name.startswith("._"):
            continue
        pdfs.append(pdf)
    return pdfs


def render_pdf(pdf_path: Path, base_name: str, output_dir: Path) -> bool:
    """Render a single PDF to PNG pages. Returns True on success."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pages_dir = output_dir / f"{base_name}_{timestamp}_pages"

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"  ERROR: Cannot open PDF: {e}")
        return False

    pages_dir.mkdir(exist_ok=True)
    total = doc.page_count

    try:
        for pi in range(total):
            pix = doc[pi].get_pixmap(dpi=DPI)
            img_name = f"page_{pi+1:02d}.png"
            img_path = pages_dir / img_name
            pix.save(str(img_path))
            if (pi + 1) % 10 == 0 or pi == total - 1:
                print(f"    page {pi+1}/{total}")
    except Exception as e:
        print(f"  ERROR during render: {e}")
        doc.close()
        return False

    doc.close()
    print(f"  Done: {total} pages → {pages_dir}")
    return True


def main():
    existing = find_existing_basenames(OUTPUT_DIR)
    all_pdfs = collect_pdfs(PDF_ROOT)

    print(f"Found {len(all_pdfs)} PDFs in {PDF_ROOT}")
    print(f"Already rendered: {len(existing)} base names")
    print()

    skipped = []
    to_render = []

    for pdf in all_pdfs:
        base_name = pdf.stem
        if base_name in existing:
            skipped.append(pdf)
        else:
            to_render.append(pdf)

    print(f"Skip (already rendered): {len(skipped)}")
    for s in skipped:
        print(f"  ✓ {s.relative_to(PDF_ROOT)}")
    print()
    print(f"To render: {len(to_render)}")
    for t in to_render:
        print(f"  → {t.relative_to(PDF_ROOT)}")
    print()

    if not to_render:
        print("Nothing to do.")
        return

    success = 0
    fail = 0
    for i, pdf in enumerate(to_render):
        base_name = pdf.stem
        rel = pdf.relative_to(PDF_ROOT)
        print(f"[{i+1}/{len(to_render)}] {rel} ({base_name})")
        if render_pdf(pdf, base_name, OUTPUT_DIR):
            success += 1
        else:
            fail += 1
        print()

    print(f"Done. Success: {success}, Failed: {fail}")


if __name__ == "__main__":
    main()
