<!-- last_verified: 2026-06-05 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of training activity and the B2 storage behind it — runs, LoRAs produced, training-image count, and where bytes live by artifact type.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /runs/stats`, `GET /runs`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (runs, LoRAs, training images, B2 storage used)
- `apps/web/src/components/dashboard/storage-breakdown.tsx` — bar chart of B2 bytes by artifact category
- `apps/web/src/components/dashboard/recent-runs-table.tsx` — latest runs with status
- `apps/web/src/lib/queries.ts` — `useRunsStats()`, `useRuns()`
- `services/api/app/runtime/runs.py` — `GET /runs/stats`, `GET /runs`
- `services/api/app/service/runs_stats.py` — `get_runs_stats()` aggregation
- `services/api/app/repo/b2_client.py` — `list_objects()` paginated scan

## Canonical Files
- Stats aggregation: `services/api/app/service/runs_stats.py`
- Dashboard page: `apps/web/src/app/page.tsx`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /runs/stats` → `RunsStats` (total_runs, completed_runs, loras_produced, training_images, storage breakdown)
- `GET /runs` → `RunSummary[]` for the recent-runs table (newest-first)

## Flow
- Page loads → `useRunsStats` + `useRuns` fire in parallel
- Stats cards display run/LoRA/image counts and total B2 storage
- Storage breakdown aggregates a single prefix-scoped `list_objects("lora-training/")` into per-category byte totals
- Recent-runs table shows the latest runs, each linking to its run detail

## Edge Cases
- API unavailable → inline `ErrorState` with retry (not silent zeros)
- No runs yet → empty chart + empty table messages
- Large object count → `list_objects` paginates via `ContinuationToken`

## UX States
- Loading: skeleton cards + chart placeholder
- Empty: "No artifacts yet" / "No runs yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_runs.py` (`test_runs_stats_breakdown`, `test_runs_http_roundtrip`)
- Required cases: stats with a completed run, empty bucket, storage breakdown by category
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff/eslint violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [LoRA Library](lora-library.md)
