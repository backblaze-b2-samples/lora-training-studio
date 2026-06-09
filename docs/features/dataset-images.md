<!-- last_verified: 2026-06-05 -->
# Feature: Dataset Images

## Purpose
Per-run training image upload with thumbnails, dimension extraction, and add/remove.

## Used By
- UI: `/library/[runId]` Dataset tab
- API: `POST /runs/{id}/dataset`, `DELETE /runs/{id}/dataset/{image_id}`

## Core Functions
- `services/api/app/service/runs.py` — `add_dataset_image`, `remove_dataset_image`
- `services/api/app/service/metadata.py` — `extract_metadata` (image dims)
- `apps/web/src/components/runs/dataset-grid.tsx`, `run-asset-image.tsx`

## Canonical Files
- Dataset service: `services/api/app/service/runs.py`
- Dataset UI: `apps/web/src/components/runs/dataset-grid.tsx`

## Inputs
- file: image (jpeg/png/webp/gif), multipart
- run_id, image_id (for delete)

## Outputs
- `DatasetImage` (image_id, key, filename, size, content_type, width, height)
- Side effect: image stored at `lora-training/{run_id}/dataset/{image_id}.{ext}`; manifest updated

## Flow
- Drag/drop or browse → `POST /runs/{id}/dataset` per file
- Service writes bytes to B2, extracts dimensions, appends to manifest dataset
- First image advances status to `captioning`
- Thumbnails render via presigned inline URLs (`useRunAssetUrl`)
- Remove drops the object, any tied caption, and the manifest entry

## Edge Cases
- Non-image content type → 415
- Empty file → 400
- Remove of unknown image → 404
- Dataset locked while `training`/`sampling`

## UX States
- Empty: dropzone only
- Loading: per-thumbnail skeletons
- Error: toast

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_add_dataset_image_advances_status`)
- Required cases: add image (dims extracted, status advances), remove image
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green

## Related Docs
- [LoRA Pipeline](lora-pipeline.md)
- [Captioning](captioning.md)
- [Metadata Extraction](metadata-extraction.md)
