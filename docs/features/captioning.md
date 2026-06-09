<!-- last_verified: 2026-06-05 -->
# Feature: Captioning

## Purpose
Attach a training caption to each dataset image — by hand or with a one-click auto-caption — and store captions beside the dataset on B2.

## Used By
- UI: `/library/[runId]` Captions tab
- API: `GET /runs/{id}/captions`, `PUT /runs/{id}/captions/{image_id}`, `POST /runs/{id}/auto-caption`

## Core Functions
- `services/api/app/service/captioning.py` — `get_captions`, `set_caption`, `auto_caption_all`
- `services/api/app/repo/captioner/` — `templated.py` (default), `claude.py` (optional)
- `apps/web/src/components/runs/caption-editor.tsx`

## Canonical Files
- Captioning service: `services/api/app/service/captioning.py`
- Captioner adapters: `services/api/app/repo/captioner/`

## Inputs
- image_id + text (manual edit, PUT)
- run_id (auto-caption all)

## Outputs
- `Caption` (image_id, text, key)
- Side effect: `lora-training/{run_id}/captions/{image_id}.txt`; manifest updated

## Flow
- Manual: edit a field, Save → `PUT` writes the `.txt` object + manifest
- Auto: `POST /auto-caption` reads each image, drives the configured captioner adapter (templated offline by default; Claude vision when `ANTHROPIC_API_KEY` set), writes all captions, advances status to `ready_to_train`

## Edge Cases
- Auto-caption with no images → 400
- Caption for an unknown image → 404
- Captions locked while `training`/`sampling`
- `captioner_provider=claude` without `ANTHROPIC_API_KEY` → runtime error surfaced as toast

## UX States
- Empty: "no images to caption"
- Loading: spinner on Save / Auto-caption
- Error: toast

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_auto_caption_and_full_training`)
- Required cases: auto-caption produces text from instance token, status advances
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green

## Related Docs
- [Trainer & Captioner Providers](trainer-providers.md)
- [LoRA Pipeline](lora-pipeline.md)
