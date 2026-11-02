# Combined demo verification · 2 November 2026

## Automated checks completed

- Production frontend build passed (TypeScript + Vite).
- Combined/retail backend: **24 passed** (18 existing prototype checks, 6 new combined-demo checks).
- Original bookshelf backend: **125 passed, 3 skipped**. See the baseline test suite for environment-dependent skips.
- Original auth, stream, and summary Node checks: **14 passed**.
- `git diff --check` passed; `git diff --exit-code -- bookshelf-original` passed.
- Retail photos match both original user attachments by SHA-256.
- Combined API verifies only two retail assets, no old photo-library endpoint, valid inventory partitions, unknown prices/stock/GTIN fields, selling-format separation, explicit auth for live calls, duplicate-resistant result counts, mocked selected-photo scan success, and failure without manual-sample substitution.

## Browser checks completed via local browser

- Home displays Retail and Bookshelf buttons.
- Retail opens exactly two original photos; both load successfully.
- Each photo opens the original bookshelf-style result summary and three-panel layout, with retail vocabulary and its own inventory/photo.
- Cereal results: 21 matched + 1 possible + 3 not identified = 25.
- Drinks results: 18 matched + 1 possible + 0 not identified = 19.
- Search, review acknowledgment, full-resolution photo dialog, 150% zoom, and switching shelves work.
- Recognition information describes retail/manual evidence and does not show book benchmark performance claims.
- Bookshelf opens the original Foundry gate, saved-sample continuation, upload home and F3 sample (26 + 0 + 15 = 41), with `/bookshelf` navigation intact.
- At 390 × 844, the retail photo page and results stack; no document-level horizontal overflow. Header navigation scrolls within its own region, as in the original component.
- All browser sample navigation and review checks used saved samples; no new model analysis was selected.

## Limits

No real company inference was called. Fresh inference, corporate login round-trip, grocery extraction accuracy and production hosting remain unverified. Manual saved readings are partial development annotations. Scenario inventory quantities are not photographic stock counts. Screenshots are local ignored outputs in `output/screenshots/`.

## Follow-up: low live drink-match count

The user reported only one match after a real company scan. That run was not
persisted by the original implementation, and access to the user's Chrome app
was unavailable; its exact extracted readings have not been inspected.

Fixed exact-string dependence for brand/name/variant field splits and consumer
brand/manufacturer aliases; normalize PET bottles, glass carriers, can boxes,
plural package wording, and printed count/size variants. Separate name/variant
uncertainty from irrelevant price/barcode/position or unspecified-size limits.
Keep unsupported flavours, brand/format conflicts, ambiguous identities, and
unconfirmed mini-pack quantities unresolved. Never select identities by bay.

**66 retail/combined backend checks pass**, including positive and negative
regressions and atomic saved-reading recovery. The production build passes.
An illustrative model-shaped fixture of 20 readings changed from 2 matched
identities with the previous matcher to 18 with the fixed matcher; an unsupported
Monster variant stayed unlinked. This is a regression fixture, not measured
performance on the user's live run. The original two photos and manual samples
are unchanged. A real repeat grocery scan remains necessary to check its result.

New completed retail readings are stored outside the web bundle under ignored
`output/retail-runs/`. Restore verifies bay and image hash, then reapplies current
matching with no inference. Corrupt/mismatched records do not attach to a photo;
failure preserves the preceding completed reading. Tests use isolated temporary
run directories and mock all inference. No session token/header is saved.

Browser follow-up on isolated port 8002: drinks page loads with the fallback
manual sample, the updated evidence list exposes literal transcriptions, and
no browser errors were recorded. Loading makes no inference request. The user's
existing process on port 8001 was left running and needs a restart for the new
Python matcher. Real live readings cannot be reconstructed from the previous
unsaved run.
