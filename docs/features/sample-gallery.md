<!-- last_verified: 2026-06-05 -->
# Feature: Sample Gallery

## Purpose
Show the sample images a run produced at each checkpoint step and at the end, viewed via presigned URLs.

## Used By
- UI: `/library/[runId]` Samples tab
- API: `GET /runs/{id}/asset?key=...` (presigned inline URL)

## Core Functions
- `services/api/app/repo/trainer/simulated.py` — `_render_sample` (Pillow PNG)
- `services/api/app/service/runs.py` — `get_asset_url`
- `apps/web/src/components/runs/sample-gallery.tsx`, `run-asset-image.tsx`

## Canonical Files
- Sample rendering: `services/api/app/repo/trainer/simulated.py`
- Gallery UI: `apps/web/src/components/runs/sample-gallery.tsx`

## Inputs
- run_id
- sample key (must belong to the run prefix)

## Outputs
- `{ url }` presigned inline URL for each sample image
- Side effect (during training): `samples/step-{NNNNNN}/sample-{NN}.png`, `samples/final/sample-{NN}.png`

## Flow
- The trainer renders deterministic placeholder PNGs per milestone step and a final set, writing them to B2
- Each sample is recorded in the manifest with its step (or null for final)
- The gallery groups samples by step (final last) and renders each via a presigned inline URL

## Edge Cases
- No samples yet → empty state
- Cross-run key → 400 (asset key must match the run prefix)
- Missing asset → 404

## UX States
- Empty: "no samples yet"
- Loading: per-image skeletons
- Loaded: grouped grids

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_auto_caption_and_full_training`, `test_asset_url_rejects_cross_run_key`)
- Required cases: samples produced during a run, cross-run asset rejected
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green

## Related Docs
- [Training](training.md)
- [LoRA Library](lora-library.md)
