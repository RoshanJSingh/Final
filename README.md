# Shelf Check · Retail & Bookshelf

One home screen offers **Retail** and **Bookshelf**. Retail uses exactly the two supplied grocery photographs and the same catalogue/photo/review panels and results summary as the original bookshelf demo. The original source in `bookshelf-original/` is unchanged.

## Run locally

Requires Python 3.13 and Node 22.12+.

```sh
cd /Users/roshansingh/Desktop/Final_demo/Retail_demo
python3 -m venv retail-app/.venv
retail-app/.venv/bin/python -m pip install -r retail-app/requirements.txt
npm --prefix retail-app/app ci
bash run_demo.sh
```

Open **http://127.0.0.1:8001/**. `PORT` and `HOST` can override the launcher defaults.

- `/` — Retail and Bookshelf buttons.
- `/retail` — exactly two photo choices.
- `/retail/analysis?bay=bay_cereal` — cereal catalogue, photo, and review checks.
- `/retail/analysis?bay=bay_drinks` — soft drink and multipack catalogue, photo, and review checks.
- `/bookshelf` — original bookshelf home, Foundry authentication, upload flow, six samples, analysis and model comparison.

Retail accepts no additional photos. The six-image source archive is retained for provenance but is not exposed by the combined app. The two active retail JPEGs match the user attachments byte-for-byte. Original bookshelf photos remain available only for the bookshelf workflow.

## Retail inventory and sample evidence

`retail-app/data/retail-inventory.json` is an inspectable inventory and annotation manifest. Rebuild its store/scan fixtures with `python3 retail-app/scripts/build_retail_data.py` (the launcher does this automatically).

- 25 cereal identities, separated by product name and visible variant. Repeated cartons and carton sizes are grouped when size has not been transcribed.
- 19 drink identities, separated by name, variant and selling format. Plastic bottles, glass multipacks, mini-can packs and can cartons have different internal IDs.
- Internal IDs are demo catalogue identities, not verified retailer SKUs or GTINs. Unknown sizes, prices, sales rates, exact facings and true physical stock are `null`.
- Scenario on-hand quantities are **12 cereal selling units** or **8 drink selling units** per catalogue entry. A multipack/case is one selling unit. These quantities are simulated, not counted from the image.
- Saved readings are **partial manual transcriptions**, with representative estimated package boxes. Cereal: **21 matched + 1 possible + 3 not identified = 25**. Drinks: **18 matched + 1 possible + 0 not identified = 19**.
- Three cereal names visible in top overstock are in the catalogue but intentionally outside the saved front-shelf transcription. They are described as not transcribed, not missing stock. The cropped Raisin Bran carton and silver Monster can require identity review. No silver-can flavour is guessed.
- Gaps trigger a general shelf-layout check, never an invented missing SKU. Review actions change only session acknowledgements and never inventory or the result counts.

These are generic retail scenes, not verified Albertsons stores. Source and publisher-declared licence are recorded in `retail-images/manifest.json`. No grocery accuracy or ROI claim is made.

## Fresh analysis

Saved samples work without company sign-in or inference. To run a new analysis, sign in with Straive and explicitly select **Run a new analysis**, then **Analyze again**. Retail reads the chosen original photo using the grocery prompt; the catalogue is not passed to the model. Matching accepts equivalent brand/name/variant field splits and common package wording, then checks the visible selling format. Unreadable price, barcode, location, or an unspecified size do not invalidate a readable product identity; required mini-can sizes and pack counts still need confirmation. Unknown or conflicting attributes remain for review. Failure preserves the current UI result and never substitutes the manual sample.

Live company authentication and real grocery inference quality have not been validated here. All development inference checks were mocked; no paid model call was made. Completed retail readings are saved locally under ignored `retail-app/output/retail-runs/`, with the photo hash and raw structured evidence. Reloading restores and recompares the last completed reading without a new model call. Failed scans preserve the last completed reading; no company session token is stored. Runs made before the matching fix were not retained and require one fresh explicit analysis.

## Validation

```sh
cd retail-app
.venv/bin/python -m pytest -q
npm --prefix app run build
cd ../bookshelf-original
../retail-app/.venv/bin/python -m pytest -q
node --experimental-strip-types --test qa/test_scan_stream.mjs qa/test_foundry_auth.mjs qa/test_analysis_summary.mjs
```

See `retail-app/qa/COMBINED_DEMO_QA.md` for browser checks. Changes remain local; no push, PR, or deployment was requested.
