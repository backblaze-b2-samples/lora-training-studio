<!-- last_verified: 2026-06-08 -->
# Feature: Training

## Purpose
Drive a run through training, streaming step progress, a loss curve, intermediate checkpoints, and sample images to B2 — simulated by default so it runs anywhere, with an opt-in **real** on-device trainer (SD 1.5 LoRA) for those with a GPU/MPS.

## Used By
- UI: `/library/[runId]` Training tab
- API: `POST /runs/{id}/train`, `GET /runs/{id}/progress`
- Job: `run_training_job` via `BackgroundTasks`

## Core Functions
- `services/api/app/service/training.py` — `start_training`, `run_training_job`
- `services/api/app/repo/trainer/` — `simulated.py` (default), `local.py` + `_sd_lora.py` (real SD 1.5 LoRA, opt-in), `replicate.py` (stub)
- `apps/web/src/components/runs/training-monitor.tsx`

## Canonical Files
- Training orchestration: `services/api/app/service/training.py`
- Trainer exemplar: `services/api/app/repo/trainer/simulated.py`

## Inputs
- run_id (must have dataset + captions)

## Outputs
- `TrainingProgress` (current_step, total_steps, loss_curve, latest_checkpoint_key, message)
- Side effects: `checkpoints/step-*.bin`, `samples/step-*/*.png`, `samples/final/*.png`, `lora/{run_id}.safetensors`; manifest status transitions

## Flow
- `POST /train` validates dataset + captions, flips status to `training`, schedules the background job
- The job drives the configured trainer; on each step it persists a loss point, the latest checkpoint key, and sample keys into the manifest
- On completion: final samples + LoRA written, status → `complete`
- The UI polls `GET /progress` (via `useRunProgress`) while in flight
- The simulated trainer emits a synthetic decreasing loss curve over a few wall-clock seconds — no GPU, no keys
- The optional `local` trainer (`TRAINER_PROVIDER=local`) runs a real diffusers + peft SD 1.5 LoRA loop on MPS/CUDA, emitting a real loss curve, real checkpoints, and real generated samples to B2 — a multi-minute job; see [Trainer & Captioner Providers](trainer-providers.md)

## Edge Cases
- Train without dataset → 400; without captions → 400
- Train while already training → 409
- Trainer raises → status set to `failed`, message recorded (run never crashes)
- Run deleted mid-flight → job notices a missing manifest and stops

## UX States
- Pre-train: empty-state prompt
- Training: progress bar + live loss line chart
- Complete: full loss curve

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_auto_caption_and_full_training`, `test_train_requires_captions`)
- Required cases: full run completes with LoRA + samples + decreasing loss, train blocked without captions
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green

## Related Docs
- [Trainer & Captioner Providers](trainer-providers.md)
- [Sample Gallery](sample-gallery.md)
- [LoRA Pipeline](lora-pipeline.md)
