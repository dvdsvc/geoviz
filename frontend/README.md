# GeoViz frontend

[Project overview](../README.md) · [中文说明](../README.zh-CN.md) · [Running guide](../docs/running.md)

This is the preserved Next.js 16.2.5 / React 19 research interface. The showcase uses eight synthetic samples and 48 synthetic spots. Files named `realSamples.json` and `realSpots.json` retain legacy import names; they contain generated fixtures in this copy.

From the repository root:

```bash
npm --prefix frontend ci --ignore-scripts --no-audit --no-fund
npm --prefix frontend run dev -- --hostname 127.0.0.1
npm --prefix frontend run build
npm --prefix frontend run typecheck
```

Start the backend separately using the root running guide. `NEXT_PUBLIC_API_URL` selects the backend address at startup/build time. Only public addresses and tile settings belong in frontend environment variables. The main sample/spot data is bundled statically; provenance is fetched from the backend.

Full `npm --prefix frontend run lint` currently reports five legacy React-rule errors and nineteen warnings; see [validation](../docs/validation.md). Type checking, build and functional numerical checks are recorded separately. Original scientific utilities and the interface structure are preserved.
