# Local validation

[Overview](../README.md) · [Running](running.md) · [Verification JSON](../evidence/local_verification.json)

Preparation and verification: **2026-10-26–27**. This independent local snapshot was checked using Python 3.12 and an isolated dependency environment, together with the frontend's original npm lock file. No real model API was called and no original research file was edited.

## Functional and numerical checks

|Check|Observed behavior|
|---|---|
|TypeScript|`npm run typecheck` passes.|
|Production build|Next.js 16.2.5 builds the application and generates its static routes successfully.|
|API and data contract|Synthetic health mode, 8 samples, 48 spots, source-page data and image serving, and a four-match keyword query are checked through FastAPI TestClient. Optional model/index routes return 503 in demo mode.|
|Backend age calculation|Six controlled measurements yield 103.0 Ma, error 0.5774 Ma and MSWD 6.2.|
|Frontend numerical functions|The same weighted result, KDE peak 105 Ma, minimum apparent age 100 Ma and concordia round trips at five ages pass.|
|Knowledge graph|Preserved graph code constructs 30 nodes and 102 edges from the eight synthetic records.|
|Source text matching|The preserved PDF matcher locates controlled text on page 1 of a newly generated PDF with a nonempty box and `page_lcs_fuzzy` match method.|
|Repository checks|Source hashes, syntax, JSON/TOML/SVG, bilingual structure, local links, exclusions, sensitive-pattern scan and payload sizes are checked.|

These are focused checks of real code on synthetic inputs, not a dataset-accuracy evaluation. The demonstration source page uses fixed synthetic boxes; the generated-PDF check separately exercises the matching algorithm. The numerical checks assume valid positive uncertainties.

## Browser inspection

The local interface was actually opened, rather than inferred from source alone. Sample selection, the weighted-age display, source-page loading and normalized-box highlighting were inspected. [Weighted-age screenshot](../assets/screenshots/weighted-mean.jpg) · [Source-highlight screenshot](../assets/screenshots/provenance.jpg). These screenshots contain only synthetic records. Additional exercised interactions are listed in the verification JSON; do not interpret a source-level feature inventory as a claim that every optional provider integration was run.

The first map view showed the old CARTO endpoint's API-key-required response. The copy now uses a configurable OpenStreetMap default and visible attribution, and the working base map was inspected after reload. Map tiles still depend on the external provider and network.

## Retained lint findings

Full `npm run lint` reports **5 errors and 19 warnings** under the current eslint-config-next/React rules. The errors concern refs during render in `GlobeView`, declaration ordering in `ProvenanceViewer`, and synchronous effect state updates in `useProvenance`/`useSpots`. Warnings include unused values and hook dependencies. The source algorithms were not rewritten to silence these findings. Type checking and the production build pass; they are distinct checks and do not imply that lint passes.

The CI workflow gates build, types, numerical/API checks and repository structure. Lint runs as a visible non-gating diagnostic. No hosted GitHub Actions run is claimed.

## Dependency and execution scope

Python dependencies are locked. PyMuPDF 1.26.3 preserves the source's `fitz` interface without adopting the newer PDF/ML stack introduced by an unconstrained initial resolution. The final backend/PDF checks use the pinned environment. Optional Chroma/Gemini retrieval dependencies are recorded but not installed/exercised by the default checks. Initial environment/process restrictions on the frontend compiler were resolved by running the normal local build with its required worker-process access; no build bypass or algorithm change was used.

Original-source before/after fingerprints, original Git status/diff identities, candidate file sizes and archive checks are recorded in the separate local owner report. A heuristic secret scan is useful evidence, not proof of complete security or licensing clearance. Private source credentials were excluded from copied files and were not exposed in the report.
