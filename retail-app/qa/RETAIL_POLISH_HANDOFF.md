# Retail polish — 2 November 2026

Implemented in `Desktop/Final`; the attachment's older project path does not exist. Widespread pre-existing modifications and staged changes were preserved. No commit, push or deployment. Windows virtual environment, node_modules, dependency pins, Foundry endpoint/project/authentication, ports and launchers were not changed. Bookshelf source was not edited.

## Confirmed diagnosis

Both image-hash-validated saved runs exist: 141 cereal observations and 244 drink observations, with per-section usage. These are saved model readings, separate from manual samples. Their original inference was not executed in this session or independently authenticated with Foundry.

- **Field interpretation:** 172/244 drink readings have null product_name_text, often with usable brand/variant/format. Version 3 rejected these immediately. Version 4 accepts a restricted set of consumer family names in brand_text. Manufacturer-only text still cannot establish a product.
- **Cereal fields:** `Cheerios / OAT CRUNCH / CINNAMON` needed the variant repeated in one field. A partial variant is now accepted only when the combined fields supply the full catalogue variant. Vanilla alone still does not select Orange Vanilla.
- **Crop placement:** Saved runs include lower shelves and edges. Old y starts were 0, 1360, 1424: the last two rows overlapped by 1536/1600 pixels. New starts are 0, 712, 1424, still nine native-resolution crops with full edge coverage. Fresh extraction quality is unverified.
- **Resolution:** The app sends original-resolution PNG crops, not a downscaled full photo. Provider-internal resizing is unknown.
- **Duplicates:** The combined path previously did no observation suppression. Unique identity totals already used sets. Suppression now requires equal evidence, different crops and box IoU ≥0.8. Adjacent packages, conflicting variants and missing geometry are retained. Original saved evidence is untouched; diagnostic links retain suppressed observation IDs. This is not a physical-stock count.
- **Incomplete evidence:** Mini-can readings often say `7.5 oz`, not explicit fluid ounces; Fanta sometimes lacks size/count; Monster labels are incomplete; cereal variants sometimes contain marketing text. These remain unresolved where required evidence is missing. No blanket fuzzy acceptance was introduced.
- **Partial failure:** Existing all-or-nothing extraction and bounded split retry remain. Failed scans preserve completed results. UI text now explains that oversized sections may be split rather than claiming exactly one reading per section.
- **Restoration:** Existing photo hashes and recomparison prevent wrong-image/current-matcher confusion. New saves also record extraction/prompt/matcher versions. Old saves remain compatible but their capture prompt version is unknown.
- **UI:** A synchronous controller guard blocks rapid duplicate submission. Bay changes clear review acknowledgements/highlights. Raw observed text remains beside catalogue identities in inspect/review. Live results clear stale manual-sample derived fields. Acknowledgements do not change matching totals.

The historical one-product failure was **not reproduced**: the captured current matcher produces 4/19 drink identities from the available run. Different older code or an unsaved reading could explain it, but that is a hypothesis. A complete package-by-package ground truth has not been established; we cannot classify every unmatched item as unread by the model. No evidence showed correct matched identities being lost from the set-based summary.

## Evaluation

From the project root on Windows:

```powershell
.\retail-app\.venv\Scripts\python.exe .\retail-app\scripts\evaluate_identity.py
```

Inspect `qa/evaluation/cases.json`, `results.json`, frozen `identity_v3.py` and baseline hashes. The 23 cases contain 14 literal saved observations from both photos and 9 labelled synthetic regressions. Selected labels were checked against the source photos; uncertainty was preserved. This is a development/regression set, **not blind held-out evaluation**, and no judge supplied its own ground truth.

| Approach | Correct automatic / supported | Incorrect / automatic | Appropriate abstentions | Possible/review |
|---|---:|---:|---:|---:|
| A: captured v3 | 5/13 | 0/5 | 10/10 | 1/23 |
| B: v4 | 13/13 | 0/13 | 10/10 | 4/23 |
| C: hybrid | Not evaluated live | — | — | Mocked contract checks only |
| D: judge all | Not run | — | — | Optional bounded comparison |

Independent retrieval coverage is 16/16 labelled candidate targets. This does not establish coverage for all saved observations. Across all saved readings, automatic acceptance changes from **23/244 to 71/244 drinks**, **55/141 to 58/141 cereal**. Unique accepted identities change **4/19 to 14/19 drinks**, **21/25 to 21/25 cereal**. These acceptance counts are not correctness or end-to-end accuracy metrics. Improvement comes from interpreting existing extraction fields, not new extraction or manual review.

Historical usage recorded in the saved files: cereal 9 calls / 59,926 total tokens; drinks 11 calls / 93,843 total tokens, including a truncated parent and split children. Historical latency/pricing are unavailable; cost is not invented. This session made zero model calls. Results JSON records local matcher latency.

## Judge decision

Keep deterministic matching enabled. The optional text judge is experiment-only, not wired into the normal scan endpoint. It uses the existing Foundry infrastructure, 30-second deadlines, at most one retry, strict parsing, candidate-ID and packaging/count checks, deterministic fallback, and a cache tied to observation, full catalogue, endpoint/project, prompt content/version and matcher version. New judge recommendations remain possible matches unless the **full catalogue** deterministic matcher independently supports them. Assertions or confidence cannot create automatic identities.

A later explicitly chosen experiment can use the existing session token in `RETAIL_JUDGE_TOKEN` (never a command argument):

```powershell
.\retail-app\.venv\Scripts\python.exe .\retail-app\scripts\evaluate_identity.py --judge hybrid --max-observations 10 --output .\retail-app\output\judge-hybrid.json
```

Bound: 10 observations, at most 20 calls, 2,048 output tokens per call, no image inference. `--judge all` uses the same cap for comparison. Usage and proposals are saved; cost remains unknown. This command was not run. Review proposals against independent labels before any deployment decision.

## Inventory and limitations

Both original photographs were inspected. Existing catalogue semantics are retained: 25 cereal groups, 19 drink groups, separate flavours/formats, unknown exact sizes/GTINs/physical stock, simulated quantities, uncertain silver Monster, and no stockout inference from gaps. No catalogue quantities, prices or identities were invented. Top-overstock cereal items omitted from the partial manual front-shelf sample are not absent stock. Some marketing-heavy or incomplete observations remain unlinked. Conservative deduplication intentionally retains possible duplicates when evidence disagrees.

Two photos cannot establish general retail accuracy. No fresh extraction, live judge evaluation, Windows runtime or interactive desktop/mobile browser validation was performed here. Crop/prompt effects need your live testing. All existing regression tests and new judge success/cache/invalid/timeout/fallback tests are offline.

## Try it on Windows

Use your existing working environment. From your Windows project root:

```powershell
.\retail-app\.venv\Scripts\python.exe .\retail-app\scripts\build_retail_data.py
npm --prefix .\retail-app\app run build
Set-Location .\retail-app
.\.venv\Scripts\python.exe -m uvicorn demo:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/. No environment recreation or configuration changes are required. Existing `output/retail-runs` files recompare on reload without inference. Only a new explicit analysis tests the changed crop/prompt. The frontend must be rebuilt; otherwise the server may serve an older dist.

1. Verify Retail/Bookshelf home choices and exactly two Retail photos.
2. Open each bay and refresh: saved live evidence should restore without new inference. Inspect literal text and the summary/filter/detail identity partition.
3. Choose Saved sample analysis → Reload sample to inspect the manual sample separately. Refresh restores the last saved live run.
4. Sign in normally; choose Run a new analysis → Analyze again. Rapid double-click should start only one scan.
5. Cancel/interrupt a scan, confirm the prior completion remains, then retry explicitly. Failed partial scans must not become completed results.
6. Check review acknowledgements, keyboard dialog open/Escape/focus return, 390px mobile layout, and your usual Bookshelf sample/live flow.

Offline commands: from `retail-app`, `.\.venv\Scripts\python.exe -m pytest -q`; from `bookshelf-original`, `..\retail-app\.venv\Scripts\python.exe -m pytest -q`.

Validation used temporary macOS environments with unchanged dependency pins: retail 76 tests passed; original Bookshelf 125 passed / 3 skipped; frontend production build passed. Browser and company inference tests remain with you.
