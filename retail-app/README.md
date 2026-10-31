# Straive Shelf Check · Grocery shelf audit

A working, deliberately conservative concept built from section A of
`planning/Albertsons_Retail_Prompts.md`. The original company application in
`bookshelf-original/` is unchanged. No commits, deployments or paid inference calls
were made during implementation.

## Start

Python 3.13 and Node 22.12+ are required (this environment uses Node 24).

```sh
cd /workspace/Retail_demo/retail-app
export UV_CACHE_DIR=/workspace/.cache/uv
uv venv --allow-existing --python /usr/bin/python3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
npm --prefix app ci --include=dev --cache /workspace/.cache/npm --no-audit --no-fund
bash run_demo.sh
```

The launcher builds the frontend and serves the app on loopback port 8001.
`PORT` and `HOST` can override it. For frontend development, run
`.venv/bin/python -m uvicorn retail.main:app --port 8001` and, in a second terminal,
`npm --prefix app run dev`; Vite proxies the API and photos. Processes must restart
after restoring an environment snapshot. No external database is needed.

## A truthful walkthrough

1. Open the saved cereal sample. The original photograph is generic retail imagery,
   not a verified Albertsons store. Three partial manual product-name readings are
   paired with a **simulated** six-SKU assortment. Variant, size, pack and location
   evidence is deliberately unknown: **0 found + 6 review + 0 not observed = 6**.
2. Select Corn Chex. Two catalogue sizes remain candidates. No size is guessed and
   no outline is invented. Illustrated carton icons are not reference packshots.
3. Change the comparison bay to Pantry essentials. Its two fictional expected SKUs
   are not observed. This does not mean confirmed out of stock. No inference runs.
4. Mark a task checked or request a close-up. These dated session decisions do not
   change readings, metrics or inventory. They reset when the page reloads.
5. Inspect the six-image library, zoom the photo or open the technical evidence
   view. Original Product/Price boxes are separate from SKU evidence.
6. Upload a JPEG/PNG/WebP. Upload and refresh do not start a scan. A Straive session
   and an explicit **Analyze photo** action are required for a live request, which
   may be billable. Cancellation/failure preserve prior completed results.

## Implementation

- `retail/models.py`: versioned product observation, master, allocation, label,
  extraction, comparison and task contracts.
- `retail/compare.py`: visible-conflict rejection, compatible-unit normalization,
  GTIN checksum checks, conservative identity matching and crop-sighting fusion.
  Bay membership never resolves identity. Ambiguous observations expose every
  candidate; expected SKUs touched by that ambiguity go into review unless found
  separately. Found/review/not-observed partition unique expected SKUs.
- `retail/main.py`: sample, upload, saved-result, comparison and cancellable SSE
  endpoints. Completed results use the baseline atomic writer. Authentication,
  image loading and provider stream parsing reuse baseline code through imports;
  baseline source is untouched. Uploads and audits belong to `retail-app/output/`.
- `app/src/foundryAuth.ts`: unchanged copy of company session/login integration.
  Transient session token; no personal-key form, persisted token or auth logging.
  TLS verification remains enabled. Recognition receives no catalogue or bay list.
- `app/src/main.tsx`, `style.css`: responsive three-panel workspace, accessible
  controls, filters, photo zoom, review queue, evidence modal and provenance library.
  No remote fonts, packshots or third-party UI asset requests are required.
- `data/`: versioned simulated catalogue and partial manual development readings.
  See `annotation-notes.json`. The original image and annotation manifest is
  `../retail-images/manifest.json`; all six image hashes were checked. Publisher:
  Humans in the Loop; publisher-declared CC0. Source images and annotations remain
  unchanged, and are served directly rather than copied into the frontend bundle.

Physical package sightings are not unique SKUs or total stock. High-overlap sightings
from different crops merge only when all identity fields agree and neither is
partial. Unknown geometry and partial boundaries prevent a reliable facing count.
This heuristic needs held-out detection evaluation; it is not a validated detector.
Labels remain separate, with no inferred price-to-product association. Exact slot
compliance is unavailable because there is no mapped slot planogram.

## Validation

```sh
.venv/bin/python -m pytest -q
npm --prefix app run build
node qa/browser.cjs
```

The browser check requires Playwright (available globally in this cloud machine)
and Chromium at `/usr/bin/chromium`, and the server on port 8001. It mocks company
authentication and every analysis request. Screenshots go to ignored
`output/screenshots/desktop.png` and `mobile.png`.

Verified: 18 backend tests, production build, desktop/mobile browser checks, actual
local uploads and refresh, zoom, evidence, search, reviews, sample accounting,
zero-inference bay recomparison, mocked provider SSE crop mapping, API failures and
stream cancellation. No actual company inference was called.

## Pilot inputs still needed

The partial manual readings are development annotations, **not independent exact-SKU
ground truth** or an exhaustive scan. Obtain independently reviewed instance/SKU
annotations, a frozen held-out capture-session split and an approved assortment
before reporting accuracy. Real SKU metadata, GTINs, licensed packshots, retailer
feeds and slot mapping are not supplied. The sample sizes are simulated, not
verified attributes of the photographed products.

Live company login/authorization and grocery inference quality have not been tested.
The experimental 1600px/15% overlap crop settings, bounded output-limit recovery,
matching/fusion rules, latency and cost require evaluation. Provider schema support
and any corporate-network access must be verified in the company environment.
The UI exposes errors rather than substituting sample readings for live failures.
No retailer-system adapter is connected, and there are no inventory writes,
ordering, expiry checks, stockout claims or measured ROI.
