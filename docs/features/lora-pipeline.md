<!-- last_verified: 2026-06-05 -->
# Feature: LoRA Pipeline

## Purpose
The end-to-end run state machine that ties dataset, captions, training, samples, and download into one tracked lifecycle.

## Used By
- UI: `/train` (create), `/library/[runId]` (drive)
- API: `POST /runs`, `GET /runs/{id}`, `DELETE /runs/{id}`
- Job: training `BackgroundTasks` (see [Training](training.md))

## Core Functions
- `services/api/app/types/runs.py` — `RunStatus`, `RunConfig`, `RunDetail`, `StageState`
- `services/api/app/service/runs.py` — `create_run`, `get_run`, `list_runs`, `delete_run`, stage derivation
- `services/api/app/repo/runs_store.py` — manifest read/write, prefix helpers
- `apps/web/src/components/runs/run-detail.tsx`, `pipeline-stepper.tsx`

## Canonical Files
- Run orchestration: `services/api/app/service/runs.py`
- Manifest store: `services/api/app/repo/runs_store.py`

## Inputs
- name: string (source: Train form)
- config: RunConfig (base_model, instance_token, steps, rank, learning_rate)

## Outputs
- `RunDetail` with status, stages, dataset, captions, progress, samples, lora_key
- Side effect: `lora-training/{run_id}/run.json` manifest on B2

## Flow
- `POST /runs` writes a manifest (`status=created`)
- Status advances as artifacts appear: `captioning` (image added) → `ready_to_train` (captions) → `training` → `sampling` → `complete`
- Stage states are derived from manifest data, not stored separately
- `DELETE /runs/{id}` removes the entire run prefix

## Edge Cases
- Invalid run id → 400
- Unknown run → 404
- Delete of a run with no objects → 404

## UX States
- Empty: no runs
- Loading: skeleton on run detail
- Error: inline `ErrorState`

## Verification
- Test files: `services/api/tests/test_runs.py`
- Required cases: create+get, status advance on dataset add, full lifecycle, delete clears prefix
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no lint violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [Training](training.md)
