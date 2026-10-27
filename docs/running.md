# Running, data replacement and optional integrations

[Overview](../README.md) · [Architecture](architecture.md) · [Data](data.md) · [Validation](validation.md)

## Local synthetic demonstration

Use Python 3.12 and Node 24 or later. The lock files describe the verified Python and JavaScript dependency sets. From the root:

```bash
uv sync --locked
npm --prefix frontend ci --ignore-scripts --no-audit --no-fund
uv run --locked uvicorn --app-dir backend main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
npm --prefix frontend run dev -- --hostname 127.0.0.1
```

Visit `http://localhost:3000`. The banner and sample identifiers clearly indicate synthetic data. `/api/health` reports `mode: synthetic-demo`. No provider credential is needed. Sample search supports the added local keyword demonstration, not natural-language inference; try `凝灰岩`, `DEMO01` or `全部`. Optional vector/GraphRAG model/index routes return 503 in this mode.

The blank `.env.example` files are templates. The backend does not automatically load the root template. Export only the settings you intend to use in the process environment; do not blindly load blank path values from the template. Next.js reads its frontend environment at development startup/build time. Provider secrets belong only in the backend environment.

## Build and checks

```bash
npm --prefix frontend run build
npm --prefix frontend run typecheck
uv run --locked python -B scripts/check_backend.py
node scripts/check_science.mjs
uv run --locked python -B scripts/check_repository.py
```

`next build` generates Next.js environment/type files. `check_backend.py` exercises actual FastAPI routes, source-page serving, a graph built from synthetic samples, weighted age calculations and PDF text matching. `check_science.mjs` loads the preserved TypeScript numerical functions using Node's native type stripping. Full `npm --prefix frontend run lint` is available separately and has retained legacy findings described in [validation](validation.md).

For the production frontend process, after building:

```bash
npm --prefix frontend run start -- --hostname 127.0.0.1
```

This is a local research prototype. No deployment infrastructure, hosted service, user management or persistent multi-user editing layer is included.

## API and map configuration

`NEXT_PUBLIC_API_URL` selects the API base, defaulting to `http://localhost:8000`. It must be set before starting/rebuilding the frontend. During local review isolated ports were used to avoid interfering with existing projects; they are not hardcoded into the source.

The original CARTO tile address displayed an API-key-required message in the local review. The showcase now uses configurable `NEXT_PUBLIC_TILE_URL` and `NEXT_PUBLIC_TILE_ATTRIBUTION`, with the standard OpenStreetMap raster URL and visible attribution as defaults. Browser map tiles require network access; scientific calculations and the synthetic API checks run locally. Use the provider's published URL and attribution, retain browser caching/referrer behavior, and do not bulk-download or prefetch tiles. The default provider's requirements are documented in the [OSMF tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

## Research inputs

Disable demo mode only after supplying the intended data paths and credentials. Environment variables include `PIPELINE_OUTPUT_DIR`, `PAPERS_JSON`, `PROVENANCE_DIR`, `MIMO_API_KEY`, `MIMO_BASE_URL` and `MIMO_MODEL`. The active v3 loader expects a list of paper labels and matching `*_ages.json` files. Its original normalization behavior is described in [data contracts](data.md).

The current frontend imports normalized sample/spot JSON at build time. The original generators in `scripts/` preserve historical conversion logic but use different output conventions: `generate_samples.py` emits TypeScript text, whereas the current sample module imports JSON; `generate_spots.py` emits flattened JSON. Inspect the relevant script and its stdout/output target before replacing frontend inputs. Reconcile sample identities across papers, maintain spot bindings and independently verify ages/errors before using imported records scientifically. Rebuild the frontend after changing bundled inputs.

The standalone scripts retain portable `data/private/...` placeholders for historical PDF, workbook and pipeline inputs. They do not download missing observations. Some provenance scripts additionally require rendered pages or a MinerU/extraction workspace. The matcher needed by `provenance_v3.py` is included as `scripts/provenance_mapper.py`.

## Optional vector and GraphRAG paths

```bash
uv sync --locked --extra retrieval
```

This installs optional Chroma and Google model SDK dependencies; it does not acquire data or make an API request by itself. v2 requires appropriate Gemini model/embedding environment settings and a writable vector directory selected by `GEOVIZ_VECTOR_DIR`. Its lazy index loader can embed all samples when the store is empty. GraphRAG expects `graph.json`, `communities.json` and `community_reports.json` under `GEOVIZ_GRAPHRAG_DIR/graphrag_output`, plus appropriate DeepSeek and Gemini credentials. These operations can send local data/context to model services and incur charges. They were not exercised during repository preparation.

The preserved external adapter may attempt report embeddings while loading graph statistics, so `/api/graphrag/stats` is not a guaranteed network-free diagnostic in research mode. Synthetic mode blocks it to preserve the explicit no-model demonstration boundary.
