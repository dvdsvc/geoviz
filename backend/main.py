"""GeoViz FastAPI backend with RAG + MiMo LLM."""

import csv
import json
import mimetypes
import os
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from pathlib import Path
from showcase_support import LazyComponent, demo_chat

_ROOT = Path(__file__).resolve().parents[1]
DEMO_MODE = os.getenv("GEOVIZ_DEMO_MODE", "1") == "1"
if DEMO_MODE:
    os.environ.setdefault("PIPELINE_OUTPUT_DIR", str(_ROOT / "data/demo/pipeline"))
    os.environ.setdefault("PAPERS_JSON", str(_ROOT / "data/demo/papers.json"))
    os.environ.setdefault("PROVENANCE_DIR", str(_ROOT / "data/demo/provenance"))

app = FastAPI(title="GeoViz API")


@app.middleware("http")
async def demo_integration_boundary(request, call_next):
    optional = request.url.path.startswith("/api/graphrag/") or request.url.path in {
        "/api/v2/chat", "/api/v2/rebuild", "/api/v2/stats"
    }
    if DEMO_MODE and optional:
        return JSONResponse(status_code=503, content={
            "detail": "Optional model/index routes are disabled in synthetic demo mode."
        })
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional model/vector integrations load only when explicitly used.
pipeline = LazyComponent("rag", "RAGPipeline")
pipeline_v2 = LazyComponent("rag_v2", "RAGPipelineV2")
pipeline_v3 = LazyComponent("rag_v3", "RAGPipelineV3")
graphrag_engine = LazyComponent("graphrag_engine", "GraphRAGEngine")

def _query_v3(query: str) -> dict:
    if DEMO_MODE:
        return demo_chat(query, pipeline_v3.samples)
    return pipeline_v3.query(query)


class ChatRequest(BaseModel):
    query: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    """v3 query; synthetic keyword demonstration when DEMO_MODE is enabled."""
    result = _query_v3(req.query)
    # Return only the fields the frontend needs for matched sample cards
    matched = [
        {
            "sampleId": s["sampleId"],
            "region": s["region"],
            "basin": s["basin"],
            "formation": s["formation"],
            "rockType": s["rockType"],
            "ageMa": s.get("ageMa"),
            "error": s.get("error"),
        }
        for s in result["samples"]
    ]
    return {
        "answer": result["answer"],
        "matched_count": len(matched),
        "matched_samples": matched,
        "filters": result["filters"],
    }


@app.get("/api/samples")
def get_samples():
    if DEMO_MODE:
        return {"samples": pipeline_v3.samples, "count": len(pipeline_v3.samples)}
    from samples_data import SAMPLES
    return {"samples": SAMPLES, "count": len(SAMPLES)}


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "synthetic-demo" if DEMO_MODE else "research"}


# ── Grain data storage (in-memory, replace with DB for production) ────────────

# Store: { sampleId: [ {grainId, ageMa, error, ratio206_238, ratio207_235, concordance}, ... ] }
GRAIN_STORE: dict[str, list[dict]] = defaultdict(list)


class GrainRecord(BaseModel):
    sampleId: str
    grainId: Optional[int] = None
    ageMa: float
    error: float
    ratio206_238: Optional[float] = None
    ratio207_235: Optional[float] = None
    concordance: Optional[float] = None


class BulkGrainUpload(BaseModel):
    grains: list[GrainRecord]


def _compute_weighted_mean(grains: list[dict]) -> dict:
    """Compute weighted mean age, error, and MSWD from grain records."""
    ages = [g["ageMa"] for g in grains]
    errors = [g["error"] for g in grains]
    n = len(ages)
    if n == 0:
        return {"weightedMean": 0, "weightedError": 0, "mswd": 0, "n": 0}

    w_sum = 0.0
    w_total = 0.0
    for age, err in zip(ages, errors):
        w = 1.0 / (err * err)
        w_sum += w * age
        w_total += w
    mean = w_sum / w_total
    error = 1.0 / (w_total ** 0.5)

    chi2 = 0.0
    for age, err in zip(ages, errors):
        w = 1.0 / (err * err)
        chi2 += w * (age - mean) ** 2
    mswd = chi2 / (n - 1) if n > 1 else 0.0

    return {"weightedMean": round(mean, 4), "weightedError": round(error, 4), "mswd": round(mswd, 4), "n": n}


@app.post("/api/grains/bulk")
def upload_grains(payload: BulkGrainUpload):
    """Upload grain data in bulk. Grains are grouped by sampleId."""
    count = 0
    for g in payload.grains:
        record = g.model_dump()
        # Auto-assign grainId if not provided
        if record.get("grainId") is None:
            record["grainId"] = len(GRAIN_STORE[g.sampleId]) + 1
        GRAIN_STORE[g.sampleId].append(record)
        count += 1

    return {"uploaded": count, "samples_affected": len(set(g.sampleId for g in payload.grains))}


@app.get("/api/grains")
def get_all_grains():
    """Get all grains grouped by sampleId, with weighted mean stats."""
    result = {}
    for sample_id, grains in GRAIN_STORE.items():
        stats = _compute_weighted_mean(grains)
        result[sample_id] = {"grains": grains, **stats}
    return {"samples": result, "total_grains": sum(len(g) for g in GRAIN_STORE.values())}


@app.get("/api/grains/{sample_id}")
def get_grains_for_sample(sample_id: str):
    """Get grains for a specific sampleId."""
    grains = GRAIN_STORE.get(sample_id, [])
    if not grains:
        return {"sampleId": sample_id, "grains": [], "weightedMean": 0, "weightedError": 0, "mswd": 0, "n": 0}
    stats = _compute_weighted_mean(grains)
    return {"sampleId": sample_id, "grains": grains, **stats}


@app.delete("/api/grains")
def clear_grains():
    """Clear all grain data."""
    GRAIN_STORE.clear()
    return {"status": "cleared"}


# ── RAG v3 (Real data from pipeline output) ──────────────────────────────────

@app.post("/api/v3/chat")
def chat_v3(req: ChatRequest):
    """v3 query with the configured dataset and explicit demo/research mode."""
    result = _query_v3(req.query)
    return {
        "answer": result["answer"],
        "matched_count": len(result["samples"]),
        "matched_samples": [
            {
                "sampleId": s["sampleId"],
                "region": s["region"],
                "basin": s["basin"],
                "formation": s["formation"],
                "rockType": s["rockType"],
                "ageMa": s.get("ageMa"),
                "error": s.get("error"),
            }
            for s in result["samples"]
        ],
        "filters": result["filters"],
    }


@app.post("/api/v3/reload")
def reload_v3():
    """Reload samples from pipeline output."""
    n = pipeline_v3.reload()
    return {"reloaded": True, "samples": n}


# ── RAG v2 (Hybrid: Vector + Graph + Structured) ─────────────────────────────

@app.post("/api/v2/chat")
def chat_v2(req: ChatRequest):
    """Hybrid RAG: vector search + knowledge graph + structured filters."""
    result = pipeline_v2.query(req.query)
    return {
        "answer": result["answer"],
        "matched_count": result["matched_count"],
        "matched_samples": result["matched_samples"],
        "analysis": result["analysis"],
    }


@app.post("/api/v2/rebuild")
def rebuild_index():
    """Rebuild vector index and knowledge graph from pipeline output."""
    return pipeline_v2.rebuild_index()


# ── GraphRAG — Knowledge Graph Query ────────────────────────────────────────

GRAPH_FILTERED_FIELDS = {"Sample", "Basin", "Formation", "Rock_Type", "MeasurementEvent"}


@app.post("/api/graphrag/chat")
def graphrag_chat(req: ChatRequest):
    """GraphRAG global search: community-level semantic query."""
    result = graphrag_engine.global_search(req.query)
    return result


@app.post("/api/graphrag/sample/{sample_id}")
def graphrag_sample(sample_id: str):
    """GraphRAG local search: sample-level graph traversal."""
    result = graphrag_engine.local_search(sample_id)
    return result


@app.get("/api/graphrag/stats")
def graphrag_stats():
    """Get knowledge graph statistics."""
    return graphrag_engine.stats()


@app.get("/api/v2/stats")
def rag_v2_stats():
    """Get RAG v2 statistics (sample count, vector count, graph summary)."""
    return pipeline_v2.stats()


@app.get("/api/v2/samples")
def get_v2_samples():
    """Get all samples from the pipeline output."""
    from sample_loader import load_samples
    samples = load_samples()
    return {"samples": samples, "count": len(samples)}


@app.post("/api/grains/seed")
def seed_test_grains():
    """Load test grain data for demo purposes."""
    seed_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "testGrains.json")
    if not os.path.exists(seed_path):
        return {"error": "testGrains.json not found"}
    with open(seed_path) as f:
        data = json.load(f)
    GRAIN_STORE.clear()
    for record in data:
        # Support both old flat format (sampleId/ageMa/error) and new nested format (sample_id/age_206_238)
        sample_id = record.get("sample_id") or record.get("sampleId", "")
        age_obj = record.get("age_206_238") or {}
        flat_record = {
            "sampleId": sample_id,
            "grainId": int(record.get("spot_id", record.get("grainId", 0))),
            "ageMa": age_obj.get("value", record.get("ageMa", 0)),
            "error": age_obj.get("err_1s", record.get("error", 0)),
            "ratio206_238": (record.get("r206_238") or {}).get("value", record.get("ratio206_238")),
            "ratio207_235": (record.get("r207_235") or {}).get("value", record.get("ratio207_235")),
            "concordance": record.get("concordance"),
        }
        GRAIN_STORE[sample_id].append(flat_record)
    return {"seeded": len(data), "samples": len(GRAIN_STORE)}


# ── Spot data (CSV-backed) ───────────────────────────────────────────────────

SPOT_DATA: dict[str, list[dict]] = {}
SPOTS_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data", "spots.csv")


def _load_spots_csv():
    """Load spots from CSV, group by sample_id."""
    global SPOT_DATA
    if not os.path.exists(SPOTS_CSV_PATH):
        return
    with open(SPOTS_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in reader:
            # Support both old (sampleId/grainId) and new (sample_id/spot_id) column names
            sid = row.get("sample_id") or row.get("sampleId", "")
            spot_id = row.get("spot_id") or row.get("grainId", "")
            record: dict = {
                "sample_id": sid,
                "spot_id": str(spot_id),
                "s_discarded": False,
            }
            # Carry over ageMa/error for Ar-Ar data (flat fields)
            for flat_key in ("ageMa", "error"):
                if flat_key in row and row[flat_key]:
                    try:
                        record[flat_key] = float(row[flat_key])
                    except ValueError:
                        pass
            # Dynamically include any extra columns (strings stay strings, numbers become floats)
            skip = {"sample_id", "sampleId", "spot_id", "grainId"}
            for k, v in row.items():
                if k not in skip and v:
                    try:
                        record[k] = float(v)
                    except ValueError:
                        record[k] = v
            grouped[sid].append(record)
        SPOT_DATA = dict(grouped)


# Load on startup
_load_spots_csv()


@app.get("/api/spots")
def get_all_spots():
    """Return all spots grouped by sampleId."""
    return {
        "samples": SPOT_DATA,
        "total_spots": sum(len(v) for v in SPOT_DATA.values()),
    }


@app.get("/api/spots/{sample_id}")
def get_spots_for_sample(sample_id: str):
    """Return spots for one sample."""
    return SPOT_DATA.get(sample_id, [])


@app.post("/api/spots/reload")
def reload_spots():
    """Reload spots from CSV (useful after file update)."""
    _load_spots_csv()
    return {"reloaded": True, "samples": len(SPOT_DATA), "total_spots": sum(len(v) for v in SPOT_DATA.values())}


# ── Provenance data ───────────────────────────────────────────────────────────

PROVENANCE_DIR = os.environ.get(
    "PROVENANCE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "geochron_pipeline_openai", "output"),
)


@app.get("/api/provenance/list")
def list_provenance_papers():
    """List available provenance JSON files."""
    papers = []
    if not os.path.isdir(PROVENANCE_DIR):
        return {"papers": papers, "error": f"Directory not found: {PROVENANCE_DIR}"}
    for fn in sorted(os.listdir(PROVENANCE_DIR)):
        if fn.endswith("_provenance.json"):
            paper_name = fn[:-len("_provenance.json")]
            prov_path = os.path.join(PROVENANCE_DIR, fn)
            try:
                with open(prov_path) as f:
                    data = json.load(f)
                papers.append({
                    "paper_name": paper_name,
                    "short_name": paper_name.split("_")[0] if "_" in paper_name else paper_name,
                    "total_pages": data.get("total_pages", 0),
                    "total_fields": data.get("total_fields", 0),
                    "found_count": data.get("found_count", 0),
                })
            except Exception:
                papers.append({"paper_name": paper_name, "error": "failed to load"})
    return {"papers": papers, "count": len(papers)}


@app.get("/api/provenance/{paper_name}")
def get_provenance(paper_name: str):
    """Serve a single provenance JSON file."""
    prov_path = os.path.join(PROVENANCE_DIR, f"{paper_name}_provenance.json")
    if not os.path.exists(prov_path):
        return {"error": f"Provenance not found: {paper_name}"}
    with open(prov_path) as f:
        return json.load(f)


@app.get("/api/provenance/{paper_name}/pages/{filename}")
def get_page_image(paper_name: str, filename: str):
    """Serve a rendered PDF page image."""
    pages_dir = os.path.join(PROVENANCE_DIR, f"{paper_name}_pages")
    img_path = os.path.join(pages_dir, filename)
    if not os.path.exists(img_path):
        return {"error": f"Image not found: {filename}"}
    mime_type, _ = mimetypes.guess_type(filename)
    return FileResponse(img_path, media_type=mime_type or "image/png")
