# GeoViz · Geochronology Exploration and Provenance

![GeoViz workflow](assets/mark.svg)

**English** · [简体中文](README.zh-CN.md)

A research platform for exploring literature-derived geochronology records through a linked **map → sample → analytical spot → age calculation → source-page** workflow. The application combines a Next.js/React interface, a FastAPI service, geochronology utilities and several retrieval experiments. This independent showcase ships with **8 synthetic samples and 48 synthetic spots**; private research observations and papers are excluded.

## 🔬 Research purpose

Extracted geological records become useful when a researcher can inspect their location and stratigraphic context, compare samples, inspect the underlying measurements and return to the text supporting a field. GeoViz implements this interaction layer between document extraction and subsequent scientific analysis. The emphasis is traceable data exploration rather than an autonomous claim of geological discovery.

## 🗺️ Implemented workflow

|Surface|Implemented behavior|Source|
|---|---|---|
|Map and sample browser|Leaflet markers and clusters; sample grouping by reference and ID prefix; selection and comparison of up to four records|[Page](frontend/src/app/page.tsx), [MapView](frontend/src/components/MapView.tsx), [Sidebar](frontend/src/components/Sidebar.tsx)|
|Measurement exploration|Spot table, editable inclusion state and client-side age calculations|[SpotTable](frontend/src/components/SpotTable.tsx), [useSpots](frontend/src/hooks/useSpots.ts), [spotCalc](frontend/src/utils/spotCalc.ts)|
|Age and stratigraphic views|Inverse-variance weighted mean and MSWD; KDE peak; minimum apparent age; Wetherill concordia display; time-axis and built-in stratigraphic reference views|[Scientific methods](docs/methods.md)|
|Source provenance|Field list, source-page image, page navigation and normalized bounding-box highlight|[ProvenanceViewer](frontend/src/components/ProvenanceViewer.tsx), [provenance methods](docs/methods.md)|
|Natural-language access|Default research endpoint uses v3 query parsing, deterministic metadata filtering and result-bound answer formatting|[rag_v3.py](backend/rag_v3.py)|
|Retrieval experiments|v2 hybrid structured/vector/graph retrieval; separate community-report GraphRAG adapter|[Retrieval boundaries](docs/architecture.md)|

<p>
<img src="assets/screenshots/weighted-mean.jpg" width="420" alt="Weighted-age view with synthetic observations" />
<img src="assets/screenshots/provenance.jpg" width="420" alt="Generated source page and field highlight" />
</p>

Actual local screenshots using synthetic inputs: age calculation and source-field highlighting.

## ⚙️ Run the synthetic showcase

Requirements: **Python 3.12**, **Node 24+**, `uv` and npm. From the repository root:

```bash
uv sync --locked
uv run --locked uvicorn --app-dir backend main:app --host 127.0.0.1 --port 8000
```

In another terminal at the same root:

```bash
npm --prefix frontend ci --ignore-scripts --no-audit --no-fund
npm --prefix frontend run dev -- --hostname 127.0.0.1
```

Open `http://localhost:3000`. Select `DEMO01`, inspect **Wtd. Mean**, **Concordia**, **Spots**, **Strat** or **View in Source**, and open the timeline. Search `凝灰岩`, `DEMO01` or `全部` for an explicitly labeled **local keyword demonstration**. Demo mode makes no model request, and optional model/index routes are disabled. This added offline search is not the historical LLM retrieval algorithm.

The source-page fixture is a generated SVG data sheet; it is not a published paper. Legacy filenames `realSamples.json` and `realSpots.json` are retained only for import compatibility and contain synthetic data in this repository. See [data contracts](docs/data.md) and [running instructions](docs/running.md).

## 🧪 Evidence and validation

The original local frontend snapshot contains **437 normalized sample records**, **330 distinct sample-ID strings**, **1,209 spot records** and **23 reference labels**. Of those spots, **1,048** have an ID present in that sample snapshot. Reused sample identifiers and unmatched records require reconciliation before treating the dataset as a clean joined research database. These are artifact inventory counts, not an extraction-accuracy evaluation. [Inventory and hashes](evidence/original_artifact_inventory.json).

The external GraphRAG artifacts contain 479 nodes, 1,174 edges and 18 community reports; they are not bundled. The default `/api/chat` research route uses v3 structured filtering, not that GraphRAG index. No retrieval-quality improvement or independent geological finding is claimed.

Local checks and their actual outcomes, including any retained lint findings, are recorded in [validation](docs/validation.md). Repeat the functional checks with:

```bash
uv run --locked python -B scripts/check_backend.py
node scripts/check_science.mjs
npm --prefix frontend run build
npm --prefix frontend run typecheck
uv run --locked python -B scripts/check_repository.py
```

## 🧠 Scientific and AI methods

The scientific utilities implement established formulas and descriptive methods; the concordia view is a visualization, not a covariance-aware concordia-age fit. Provenance matching uses text normalization, keyword matching, n-grams and LCS-based alignment to locate source text and page boxes. A successful text match supports navigation and does not validate the scientific truth of a record.

The AI contribution is integration of domain records with explicit retrieval routes, source context and interactive analysis. The v3, v2 and GraphRAG paths are described separately in [architecture](docs/architecture.md); their implementation is not presented as a new foundation model or a validated new retrieval algorithm.

## 🗂️ Repository map

```text
frontend/       Preserved Next.js interface, scientific utilities and synthetic fixtures
backend/        FastAPI, sample loader, retrieval implementations and shared clients
scripts/        Original conversion/provenance utilities; added demo and local checks
data/demo/      Synthetic pipeline-format records and generated source-page fixture
docs/           Methods, architecture, data, running, validation and provenance
evidence/       Small sanitized artifact inventories and verification records
provenance/     Original-source hashes and explicit adaptation records
```

## 🔌 Research integrations

To use private research inputs, supply explicit pipeline, paper-list and provenance paths; rebuild the frontend with authorized normalized records. Then disable `GEOVIZ_DEMO_MODE` and configure the selected model's credentials through environment variables. Optional vector/GraphRAG dependencies use `uv sync --locked --extra retrieval`; graph/community/report files and credentials are separate inputs. Index-building may call paid embedding services. See [running](docs/running.md) before enabling these integrations.

No model API was called during showcase preparation. Hardcoded credential defaults were removed from the copied modules; caches, indices, private documents and original observations are not publication candidates.

## 📚 Provenance and reuse

This is a local review snapshot prepared without changing the original project. The [source manifest](provenance/source_manifest.json) distinguishes byte-identical research files from credential/path, demo-startup and small presentation adaptations. Numerical calculation routines and provenance-matching algorithms are preserved. New synthetic fixtures, offline keyword search, checks and documentation are packaging additions.

The frontend Git history contains only the initial Create Next App scaffold; the application changes exist locally and are largely uncommitted. That history cannot establish detailed personal authorship. Confirm author/contributor attribution, rights to reused project components, dataset permissions and the final license before public redistribution. [Provenance](docs/provenance.md) · [Third-party notices](THIRD_PARTY_NOTICES.md).

Configuration: [Environment variables](docs/security.md).
