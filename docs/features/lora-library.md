<!-- last_verified: 2026-06-05 -->
# Feature: LoRA Library

## Purpose
The sample-scoped asset explorer: browse every run under the `lora-training/` prefix, open a run to view its full artifact set, and download the trained `.safetensors`.

## Used By
- UI: `/library`, `/library/[runId]`
- API: `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/asset?key=...`, `DELETE /runs/{id}`

## Core Functions
- `services/api/app/repo/runs_store.py` — `list_run_prefixes`
- `services/api/app/service/runs.py` — `list_runs`, `get_asset_url`, `delete_run`
- `apps/web/src/components/runs/run-grid.tsx`, `run-detail.tsx`, `lora-download-card.tsx`

## Canonical Files
- Library grid: `apps/web/src/components/runs/run-grid.tsx`
- Prefix-scoped listing: `services/api/app/repo/runs_store.py`

## Inputs
- None (lists all runs); run_id for detail/delete; asset key for download

## Outputs
- `RunSummary[]` (library cards), `RunDetail` (run page), `{ url }` (presigned attachment for the LoRA)

## Flow
- Library derives run ids from a single prefix-scoped listing of `lora-training/`, then reads each manifest for the card
- Run detail shows the pipeline stepper, dataset, captions, training monitor, sample gallery, and — when complete — a LoRA download card
- Download fetches a fresh presigned attachment URL on click

## Edge Cases
- No runs → empty state
- Unknown run → 404
- Download before completion → no LoRA key, card hidden

## UX States
- Empty: "no runs yet"
- Loading: skeleton cards
- Error: inline `ErrorState`

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_runs_http_roundtrip`, `test_runs_stats_breakdown`)
- Required cases: list runs over HTTP, run detail, delete
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green

## Related Docs
- [LoRA Pipeline](lora-pipeline.md)
- [File Browser](file-browser.md)
- [Dashboard](dashboard.md)
