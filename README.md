# Retail shelf-audit development kit

Inputs for adapting the original **Straive Shelf Check** application into a grocery shelf-audit concept for an Albertsons discussion. The retail adaptation has not yet been implemented.

## Repository layout

- `bookshelf-original/`: original company-auth application, including the latest local results-summary changes. Preserve this baseline; implement the adaptation in `retail-app/`.
- `planning/Albertsons_Retail_Plan.md`: researched datasets, workflow, architecture and evaluation plan.
- `planning/Albertsons_Retail_Prompts.md`: implementation instructions and proposed retail extraction prompt.
- `planning/SOURCE_SNAPSHOT.json`: original revision and SHA-256 hashes of copied source files. Includes local uncommitted UI changes; this is not a pristine checkout of that revision.
- `retail-images/`: six original-resolution retail photographs, original Product/Price annotations, preview, provenance and licence information.

The original app retains Straive Foundry login and inference integration. No personal API keys or session tokens are included. The retail photographs are generic retail scenes, not verified Albertsons stores. Their annotations do not establish exact SKUs, expected assortment or stockouts. Historical bookshelf scores do not measure retail performance.

Retail image publisher: [Humans in the Loop](https://humansintheloop.org/resources/datasets/supermarket-shelves-dataset/), published as CC0; downloaded from its [Kaggle account](https://www.kaggle.com/datasets/humansintheloop/supermarket-shelves-dataset). See `retail-images/README.md` and `manifest.json`. The original book benchmark is [Bookshelf Benchmark](https://atharva-729.github.io/bookshelf-benchmark/); retail dataset licensing does not apply to the original book assets or application.

## Codex cloud task

Select this repository in a Codex cloud environment. Ask Codex to inspect the source and install the Python and Node dependencies needed by the project. The original README documents runtime requirements.

Paste this task:

> Implement the retail shelf-audit application described in planning/Albertsons_Retail_Plan.md and section A of planning/Albertsons_Retail_Prompts.md. Use bookshelf-original/ as the source and retail-images/ as the already-downloaded image dataset. These repository-relative paths override all laptop paths in the planning documents. Keep bookshelf-original/ unchanged and build in retail-app/. Preserve Straive Foundry authentication. Inspect images and annotations; do not invent unreadable attributes or claim Albertsons-store provenance. Complete backend, frontend and mocked browser validation. Do not make paid inference calls, merge or deploy. Leave the changes ready for review, with validation results and local run instructions.

The two planning documents predate image acquisition: their statements that no archive has been downloaded are historical. Six selected raw photos and matching annotations are now included. Further SKU annotation and catalogue curation remain to be done.

## Validate the baseline

Run from `bookshelf-original/`, after installing dependencies:

```sh
python -m pytest -q
npm --prefix app ci
npm --prefix app run build
node --experimental-strip-types --test qa/test_scan_stream.mjs qa/test_foundry_auth.mjs qa/test_analysis_summary.mjs
```

These unit/build checks do not establish live Foundry access. Test real company authentication/inference separately in the appropriate company environment. Generated output, dependencies, screenshots and run logs are excluded from this repository.
