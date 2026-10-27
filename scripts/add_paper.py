#!/usr/bin/env python3
"""
add-paper: Register a new paper and regenerate frontend data.

Usage:
    python3 scripts/add_paper.py <paper_name> [--provenance] [--pdf <path>]

Examples:
    # Just add to samples/spots:
    python3 scripts/add_paper.py "马之力2016-浙江..._20260517_161531"

    # Add + run provenance mapper:
    python3 scripts/add_paper.py "马之力2016-浙江..._20260517_161531" --provenance --pdf "/path/to/paper.pdf"

What it does:
    1. Validates {paper_name}_ages.json exists in pipeline output/
    2. Adds paper_name to papers.json (idempotent)
    3. Regenerates samples.ts
    4. Regenerates realSpots.json
    5. If --provenance: runs provenance_mapper.py
"""

import json, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(ROOT)  # integrations/private/geo-viz
PIPELINE_OUTPUT = 'data/private/pipeline'
PIPELINE_DIR = 'integrations/private/extraction'
PAPERS_JSON = os.path.join(ROOT, "papers.json")
SAMPLES_SCRIPT = os.path.join(ROOT, "generate_samples.py")
SPOTS_SCRIPT = os.path.join(ROOT, "generate_spots.py")
SAMPLES_TS = os.path.join(PROJECT, "frontend", "src", "data", "samples.ts")
SPOTS_JSON = os.path.join(PROJECT, "frontend", "src", "data", "realSpots.json")

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_ages(paper_name: str) -> bool:
    path = os.path.join(PIPELINE_OUTPUT, f"{paper_name}_ages.json")
    if not os.path.exists(path):
        print(f"{RED}✗{RESET} Ages file not found: {path}")
        print(f"  Run pipeline first to generate {paper_name}_ages.json")
        return False
    with open(path) as f:
        data = json.load(f)
    print(f"{GREEN}✓{RESET} Found ages.json ({len(data)} records)")
    return True


def add_to_papers(paper_name: str) -> bool:
    with open(PAPERS_JSON) as f:
        papers = json.load(f)
    if paper_name in papers:
        print(f"{YELLOW}⚠{RESET} Already in papers.json, skipping")
        return False
    papers.append(paper_name)
    with open(PAPERS_JSON, "w") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    print(f"{GREEN}✓{RESET} Added to papers.json")
    return True


def regenerate() -> tuple[int, int]:
    """Run generate_samples.py and generate_spots.py. Returns (n_samples, n_spots)."""
    # Generate samples.ts
    result = subprocess.run(
        ["python3", SAMPLES_SCRIPT],
        capture_output=True, text=True,
    )
    with open(SAMPLES_TS, "w") as f:
        f.write(result.stdout)
    stderr = result.stderr
    # Parse sample count from stderr: "Total: N samples"
    n_samples = 0
    for line in stderr.split("\n"):
        if "Total:" in line and "samples" in line:
            n_samples = int(line.split(":")[1].strip().split()[0])
    # Generate spots.json
    result = subprocess.run(
        ["python3", SPOTS_SCRIPT],
        capture_output=True, text=True,
    )
    with open(SPOTS_JSON, "w") as f:
        f.write(result.stdout)
    n_spots = 0
    for line in result.stderr.split("\n"):
        if "Total:" in line and "spots" in line:
            n_spots = int(line.split(":")[1].strip().split()[0])
    return n_samples, n_spots


def run_provenance(paper_name: str, pdf_path: str | None) -> bool:
    """Run provenance_mapper.py for the paper."""
    # Create run_report.json if pdf_path provided
    if pdf_path:
        rp = os.path.join(PIPELINE_OUTPUT, f"{paper_name}_run_report.json")
        with open(rp, "w") as f:
            json.dump({"pdf_path": os.path.abspath(pdf_path)}, f)
        print(f"{GREEN}✓{RESET} Created run_report.json (pdf_path={pdf_path})")

    prov_file = os.path.join(PIPELINE_OUTPUT, f"{paper_name}_provenance.json")
    if os.path.exists(prov_file):
        print(f"{YELLOW}⚠{RESET} Provenance already exists, skipping mapper")
        return True

    print(f"\n{BOLD}Running provenance mapper...{RESET}")
    result = subprocess.run(
        ["python3", os.path.join(PIPELINE_DIR, "provenance_mapper.py"), paper_name],
        capture_output=False,  # stream output so user sees progress
    )
    if result.returncode != 0:
        print(f"{RED}✗{RESET} Provenance mapper failed (exit {result.returncode})")
        return False
    print(f"{GREEN}✓{RESET} Provenance complete")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paper_name = sys.argv[1]
    run_prov = "--provenance" in sys.argv
    pdf_path = None
    if "--pdf" in sys.argv:
        idx = sys.argv.index("--pdf")
        if idx + 1 < len(sys.argv):
            pdf_path = sys.argv[idx + 1]

    print(f"{BOLD}add-paper{ RESET}: {paper_name[:60]}...")
    print()

    # Step 1: Validate
    if not check_ages(paper_name):
        sys.exit(1)

    # Step 2: Register
    added = add_to_papers(paper_name)

    # Step 3: Regenerate
    if added:
        n_samples, n_spots = regenerate()
        print(f"{GREEN}✓{RESET} Regenerated: {n_samples} samples, {n_spots} spots")
        print(f"  samples.ts  → {SAMPLES_TS}")
        print(f"  realSpots.json → {SPOTS_JSON}")
    else:
        print(f"  (papers.json unchanged, skipping regeneration)")

    # Step 4: Provenance
    if run_prov:
        if not run_provenance(paper_name, pdf_path):
            sys.exit(1)
        print(f"\n{GREEN}✓{RESET} Paper ready. Backend will auto-discover the provenance file.")
    elif not os.path.exists(os.path.join(PIPELINE_OUTPUT, f"{paper_name}_provenance.json")):
        print(f"\n{YELLOW}Tip:{RESET} Run with --provenance --pdf <path> to generate source mapping.")

    print(f"\n{BOLD}{GREEN}Done.{RESET}")


if __name__ == "__main__":
    main()
