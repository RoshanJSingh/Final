# Combined Shelf Check application

This directory now contains the combined Retail + Bookshelf frontend. Follow the repository [README](../README.md) for installation, launch and evidence limitations.

- `demo.py` serves the combined frontend, preserves the original bookshelf API routes, and adds a two-photo retail scan endpoint.
- `app/src/BookshelfApp.tsx` retains the bookshelf flow with a `/bookshelf` route prefix.
- `app/src/components/` is copied from the original bookshelf UI and shared by both demos. `demoContext.ts` supplies retail terminology without changing bookshelf behaviour.
- `scripts/build_retail_data.py` maintains the curated catalogue and partial manual samples for the two selected images.
- `data/retail-inventory.json` records inventory assumptions, readable product identities, unknown attributes, image hashes and representative box estimates.
- `retail/recognition.py` reuses the grocery extraction implementation and adds visible package-format evidence. `retail/identity.py` matches brand/name/variant evidence and selling formats against the complete catalogue. Completed readings are stored locally by `retail/saved_runs.py` and can be re-compared without another company request.

The earlier `retail/main.py`, `compare.py`, `data/catalogue.json`, `cereal-readings.json` and annotation notes are retained as legacy prototype fixtures for their existing backend tests. They are **not** the combined demo's runtime catalogue, sample API or frontend. The old six-image library and fictional Pantry bay are not exposed by `demo.py`.

For development, run `.venv/bin/python -m uvicorn demo:app --port 8001` and `npm --prefix app run dev` in separate terminals. Vite serves the same two retail photos and proxies the API to port 8001.

## Latest retail polish

See [RETAIL_POLISH_HANDOFF.md](qa/RETAIL_POLISH_HANDOFF.md) for the saved-reading diagnosis, offline comparison, unchanged Windows setup commands, optional judge experiment, and remaining live-test checklist.
