# Third-party and source acknowledgements

GeoViz uses Next.js/React, Leaflet, Framer Motion, Lucide and other frontend packages recorded in [package.json](frontend/package.json) and [package-lock.json](frontend/package-lock.json). The backend uses FastAPI, NetworkX, OpenAI-compatible client libraries and optional Chroma/Google integrations. PDF alignment uses PyMuPDF; supporting scripts use Pillow and openpyxl. Python versions are recorded in [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock). Upstream license terms continue to apply.

The original interface was scaffolded with Create Next App. Scientific formulas, KDE, graph traversal, text normalization and LCS are established methods. Their implementation, adaptation and system integration are distinct from inventing those methods. Shared local client/matching modules and their source hashes are listed in [provenance](provenance/source_manifest.json).

The default interactive base map uses OpenStreetMap tiles with visible attribution. Users must follow the selected provider's [usage policy](https://operations.osmfoundation.org/policies/tiles/) and data attribution requirements. No tile archive is distributed. Screenshots show normal interactive viewing with the attribution visible.

No private paper, source dataset, original rendered page, embedding cache or GraphRAG report is distributed. The demonstration page and observations are generated fixtures. Built-in stratigraphic reference data remains the project's existing display table, not a newly verified authoritative standard.

Author/contributor attribution, rights to reused local project components and the intended project license require owner confirmation before public redistribution. This snapshot does not add an assumed project license.
