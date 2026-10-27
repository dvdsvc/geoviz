# Data contracts, fixtures and original artifact inventory

[Overview](../README.md) · [Running](running.md) · [Inventory JSON](../evidence/original_artifact_inventory.json)

## Bundled synthetic inputs

The publication candidate includes **8 unique sample IDs**, **48 spots**, one generated source page and **8 explicit provenance fields**. All values and locations are synthetic illustrations. `scripts/build_demo.py` deterministically regenerates these inputs without using original papers or observations.

|File|Purpose|
|---|---|
|`frontend/src/data/realSamples.json`|Normalized sample records consumed by the frontend; legacy filename, synthetic contents.|
|`frontend/src/data/realSpots.json`|Flat spot records consumed by `useSpots`; legacy filename, synthetic contents.|
|`frontend/src/data/spots.csv`|Same synthetic spot set for the backend's CSV reader.|
|`data/demo/pipeline/*_ages.json`|Synthetic extraction-style sample records for the preserved Python loader.|
|`data/demo/papers.json`|One synthetic source label, not a bibliography.|
|`data/demo/provenance/*_provenance.json`|Explicit field/page/box fixture.|
|`data/demo/provenance/*_pages/page_1.svg`|Generated data-sheet image, not a published paper.|

To regenerate only these known demo paths:

```bash
uv run --locked python -B scripts/build_demo.py
```

## Sample contract

The [TypeScript interface](../frontend/src/types/index.ts) includes independent UI `id`/`dataId`, `sampleId`, geographic fields and coordinates, basin/group/formation, rock type, dating mineral/system/technique, age/error/MSWD/grain count, interpretation descriptors, reference and remarks. The [Python loader](../backend/sample_loader.py) normalizes extraction-style records, parses age strings and GPS strings, and assigns sequential UI IDs.

Some normalization rules are domain-specific simplifications: unknown region strings default to the South China grouping; absent/unparseable coordinates become `(0,0)`; age parsing supports limited string forms. Preserve missingness and audit these rules before importing a broader dataset. The sample list may contain multiple records with the same `sampleId`, which is not equivalent to an independent globally unique specimen identity.

## Spot contract

The [spot interface and calculations](../frontend/src/utils/spotCalc.ts) use `sample_id`, `spot_id`, exclusion state, elemental values, isotope-ratio values/errors, isotope-specific age values/errors and concordance. The frontend groups by sample ID. Exclusion changes are client-session state. The backend exposes separate CSV-backed spots and an in-memory grain-upload store; a frontend toggle does not synchronize those stores automatically.

## Original local artifact counts

The original files were read only for source audit and aggregate inventory. They are excluded from the public candidate.

|Original artifact property|Observed count|Meaning|
|---|---:|---|
|Normalized sample records|437|Records in the saved frontend JSON, not necessarily unique specimens.|
|Distinct `sampleId` strings|330|Identifier strings can repeat across records and publications.|
|Reference labels|23|Distinct labels, not an independently deduplicated DOI count.|
|Spot records|1,209|Rows in the saved frontend spot JSON.|
|Spot sample-ID strings|69|Distinct IDs represented by those rows.|
|Spots with IDs present in the sample snapshot|1,048|Identifier overlap only; not verified paper/sample/age binding.|
|Spots without such a sample-ID match|161|Require reconciliation against the intended sample snapshot.|

Original-source hashes are retained in the [inventory JSON](../evidence/original_artifact_inventory.json). These counts are neither extraction recall nor precision and do not independently establish record accuracy.

The external GraphRAG output has 479 nodes, 1,174 edges and 18 generated community reports. Its artifacts are inventoried separately, remain outside the repository, and do not share an asserted one-to-one schema with the frontend's 437 records. A generated community report is not independent scientific evidence.

## Input ownership and release boundary

Private normalized observations, workbooks, PDF pages, extraction outputs, embedding caches, Chroma stores and GraphRAG reports are not distributed. The candidate retains conversion and matching code so input processing can be inspected. Historical scripts with portable placeholder paths still require the corresponding authorized data and optional extraction/MinerU environment. Confirm source-data rights and stable publication/sample identities before exporting research records into a public frontend bundle.
