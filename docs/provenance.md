# Source provenance and contribution boundaries

[Overview](../README.md) · [Source manifest](../provenance/source_manifest.json) · [Original inventory](../evidence/original_artifact_inventory.json)

## Source selection

The source is the local `geo-viz` project, including its frontend, FastAPI backend and conversion/provenance scripts. Later thesis-presentation previews were inspected as possible derivatives but were not mixed into this source snapshot. Shared MiMo/Gemini client modules and the PDF provenance mapper were copied from the adjacent local research workspace to satisfy actual imports.

The frontend has its own Git repository, whose sole committed revision is the Create Next App initial scaffold (`353659043b7a0b34c93a2d7bde283834785ceaed`). The application components, data and utilities are local modifications/untracked additions. The backend lives within the larger workspace rather than having a separately established project history. These facts support an implementation audit but do not establish personal authorship from commit attribution. The showcase does not invent a contribution history.

## Preserved research implementation

The source manifest lists logical original paths, source hashes, copied hashes and any adaptation reason. The numerical functions in `spotCalc.ts` and `concordia.ts`, the metadata loader, graph-construction logic and text alignment/matching algorithms preserve their research behavior. Existing scientific methods remain established methods; implementation and integration should not be described as algorithm invention.

Implemented project work includes the linked scientific interface, sample/spot representation, analysis views, page/box provenance interaction, query-to-filter path, hybrid retrieval routing, knowledge-graph operations and external GraphRAG integration. Exact personal versus collaborator/upstream boundaries require owner confirmation when preparing a CV or public authorship statement.

## Explicit showcase adaptations

Credential literals were removed without printing their values. Personal absolute paths in selected scripts were replaced by portable private-input placeholders. The copied API now lazily imports optional integrations, defaults to labeled synthetic inputs, and blocks optional model/index routes in demo mode. A small `showcase_support.py` provides clearly labeled keyword matching for the offline demonstration. None of those additions is a historical retrieval-quality result.

The frontend now accepts a configurable API base, escapes HTML before limited answer formatting, displays a synthetic-data label, and uses a configurable tile address with visible attribution after the original tile endpoint showed a key-required message. Package metadata adds a type-check command. These changes are listed separately from preserved scientific code.

The current normalized original data and spot JSON are excluded. New synthetic fixtures retain their legacy import filenames and are labeled in the interface, source reference, records and README. A generated SVG is used for the source-page demonstration. No paper was used to make that page. Next.js-generated `next-env.d.ts` is not treated as a research source or a publication candidate; a fresh build regenerates it.

## Added presentation and verification

Root bilingual README files, focused research documentation, package metadata/lock, environment templates, exclusions, SVG identity, CI, local checks, small verification records and synthetic screenshots are repository-preparation additions. The frontend's former template README is replaced with a short local guide. Existing application styling and research organization are preserved; full React modernization was not part of this pass.

## Publication boundary

Private observation files, PDFs/workbooks, rendered real paper pages, cache databases, embedding/vector stores, original GraphRAG reports, dependency directories and build outputs are excluded from the candidate payload. Public inventories retain aggregate counts and hashes only. The separate owner review report holds absolute source paths, source/Git preservation checks, payload size and ZIP checks.

Before public release, confirm authors/contributors, rights to reuse project components and dependencies, source-data permissions and the intended repository license. No license was selected on the owner's behalf. No public repository, commit, push, deployment or model execution was created as part of this preparation.
