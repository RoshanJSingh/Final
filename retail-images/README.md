# Six retail shelf photographs

Original-resolution JPEGs from the Humans in the Loop Supermarket Shelves Dataset, downloaded from the publisher's Kaggle account on 31 October 2026.

Publisher declares CC0 1.0; the Kaggle listing also declares CC0: Public Domain. Attribution retained for provenance. These are generic retail photographs, not verified Albertsons locations.

[Publisher and licence statement](https://humansintheloop.org/resources/datasets/supermarket-shelves-dataset/) | [Publisher Kaggle dataset](https://www.kaggle.com/datasets/humansintheloop/supermarket-shelves-dataset)

Use the numbered JPEG files as model inputs. PREVIEW.jpg is a browsing contact sheet, not an evaluation input. Images are unmodified archive originals, with no drawn annotation overlays.

| Image | Resolution | Suggested use |
|---|---|---|
| 01_cereal_variants_and_gaps.jpg | 4032 × 3024 | Best starting scene: readable cereal names, variants, repeated facings and visible gaps. Some packaging is cropped/occluded. Great Value branding is visible; do not represent this as Albertsons. |
| 02_soft_drinks_and_multipacks.jpg | 4032 × 3024 | Bottles versus multipacks, repeated products and gaps; reflective plastic and partially hidden packages. |
| 03_canned_vegetable_variants.jpg | 5472 × 3648 | Near-identical GOYA packaging with different contents; stacked instances, bilingual text and softer focus at edges. |
| 04_canned_seafood_and_shelf_labels.jpg | 5942 × 3961 | Dense canned seafood variants, electronic price labels, repeated facings and visible spaces. Price-to-product association requires annotation. |
| 05_snacks_and_occlusion.jpg | 4000 × 3000 | Flexible reflective bags, multiple scripts, angled camera and rail occlusion; useful harder case. |
| 06_dairy_repeated_facings.jpg | 5760 × 3840 | Many similar dairy bottles, size/flavour differences and Cyrillic text. International stress test, not a US/Albertsons assortment. |

Matching original annotation JSONs are in annotations/. They contain Product and Price rectangles, not product names, UPCs, expected planograms or verified stockouts. Preserve their original IDs; supply a separate independently reviewed SKU annotation layer later.

The six examples do not establish model accuracy. Some labels/sizes remain unreadable; record unknowns instead of guessing. Visible gaps are review examples, not evidence of total inventory or which missing SKU should occupy the space.

No inference calls were made. All files remain under ignored output/. See manifest.json for hashes, original names, dimensions and annotation counts.
