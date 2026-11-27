# APN application

This directory contains the runnable Agentic Perception Network application. See the [repository README](../README.md) for the project overview, architecture and footage contract.

## Start

```bash
./run.sh
```

Open [http://127.0.0.1:8766](http://127.0.0.1:8766).

The runner:

1. executes backend tests;
2. inventories the connected supermarket footage;
3. rebuilds camera-role reels when media changes;
4. runs the perception pipeline when required;
5. creates evaluation and security evidence;
6. builds the React application;
7. starts the FastAPI service.

If the surveillance drive is not connected, the service starts with cached camera-role reels and labels original source files unavailable.

## Development checks

```bash
.venv/bin/python -m unittest discover -s tests -v
cd web2
npm run build
npm run test:ui
```

## Active application paths

- `apn/` — Python package
- `config/` — store and security configuration
- `docs/` — technical documentation
- `eval/` — evaluation assets
- `tests/` — automated backend tests
- `tools/` — ingestion, perception and verification utilities
- `web2/` — active web application

## Data boundary

The current 14-clip pack is a controlled surveillance validation dataset. Metrics shown by APN are produced from its processed observation ledger. The clips do not provide synchronized identity ground truth, so cross-camera links remain uncertainty-aware and are not presented as biometric identification or benchmark accuracy.
