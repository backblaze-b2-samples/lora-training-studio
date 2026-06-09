<!-- last_verified: 2026-06-05 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with run/LoRA stats and a B2 storage breakdown by artifact type
  - Train (`/train`) — create a run (name, instance token, base model, config)
  - LoRA Library (`/library`) — sample-scoped explorer over the `lora-training/` prefix
  - Run detail (`/library/[runId]`) — pipeline stepper + dataset, captions, training monitor, sample gallery, LoRA download
  - Full-bucket file explorer (`/files`) and generic upload (`/upload`) — the reusable B2 base
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - Run lifecycle CRUD, dataset management, captioning, and training orchestration
  - B2 S3 integration via boto3 (contained in `repo/`)
  - Trainer adapters (simulated default, Replicate stub) and captioner adapters (templated default, Claude optional)
  - Image metadata extraction (dimensions, EXIF) for dataset images
  - Health check with B2 connectivity, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic models

## Run lifecycle

A run is a state machine; `RunStatus` walks forward through:

```
created -> captioning -> ready_to_train -> training -> sampling -> complete
                                                                   (+ failed)
```

- **created** — run manifest written; no images yet.
- **captioning** — at least one dataset image uploaded.
- **ready_to_train** — captions exist (manual or auto).
- **training** — the trainer is driving steps; checkpoints + samples stream to B2.
- **sampling / complete** — final sample set + `.safetensors` written; run is done.

Training runs as a FastAPI `BackgroundTasks` job. The trainer reports progress
per step; the service persists each tick (loss point, latest checkpoint, sample
keys) into the run manifest, which the UI polls via `useRunProgress`.

## B2 prefix layout (one run = one prefix)

"Versioned on B2" means **keyed/immutable retention**, not S3 bucket
versioning. No bucket-level versioning is enabled; there are no b2-native calls.

```
lora-training/{run_id}/
  run.json                               # manifest: status, config, metrics, artifact keys
  dataset/{image_id}.{ext}               # uploaded training images
  captions/{image_id}.txt                # one caption per image
  checkpoints/step-{NNNNNN}.bin          # intermediate checkpoints
  lora/{run_id}.safetensors              # final downloadable LoRA
  samples/step-{NNNNNN}/sample-{NN}.png  # sample gallery per checkpoint step
  samples/final/sample-{NN}.png
```

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client; trainer/captioner adapters) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. External SDKs (`boto3`, `anthropic`, `replicate`) only in `repo/`; the optional ones are imported lazily inside their adapter
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (runs, files, stats, upload, formatting)
    config/                Settings loaded from environment
    repo/                  B2 S3 client + run store + trainer/captioner adapters
      b2_client.py         S3 helpers (put/get/list/delete/presign)
      runs_store.py        Manifest read/write + prefix-scoped helpers
      trainer/             base.py, simulated.py (default), replicate.py (stub)
      captioner/           base.py, templated.py (default), claude.py (optional)
    service/               Business logic (runs, captioning, training, runs_stats, files, upload, metadata)
    runtime/               FastAPI route handlers (runs, files, upload, health, metrics)
  tests/                   pytest tests (structural + integration + run pipeline)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3`, `anthropic`, and `replicate` are only imported in `app/repo/`. Enforced by `tests/test_structure.py::test_external_sdks_only_in_repo`.
- **No raw dicts at boundaries**: all data crossing layer boundaries uses typed Pydantic models. (The run manifest is persisted as JSON; the service owns mapping it to/from typed models.)
- **No mutable globals**: configuration is read-only after init.
- **Validated inputs**: all HTTP inputs validated by FastAPI/Pydantic; run ids and per-run asset keys validated against the run's own prefix.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web `localhost:3000`, API `localhost:8000`)
- **Railway** — two services from the same repo; see `infra/railway/README.md`

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API). No application database — B2 is the sole data store, including the per-run JSON manifest. Listing/metadata via `list_objects_v2` / `head_object`.

## External Services

- **Backblaze B2 S3 API** — all artifact storage, retrieval, deletion, presigned URLs
- **HuggingFace Hub** (optional, `local` trainer only) — downloads the SD 1.5 base weights (~4 GB) on first real run; no key required
- **Replicate** (optional, not wired) — cloud GPU training, behind `REPLICATE_API_TOKEN`
- **Anthropic** (optional) — Claude-vision auto-captioning, behind `ANTHROPIC_API_KEY`

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins, scoped to `GET/POST/PUT/DELETE/OPTIONS`
- **API -> B2** — authenticated via application keys, signature v4, region from `B2_REGION`
- **Client -> B2** — presigned URLs (inline for thumbnails/samples, attachment for LoRA download), 10-min expiry

## Data Flows

- **Create run**: Browser -> `POST /runs` -> service writes manifest to B2 -> redirect to run detail
- **Add dataset image**: Browser -> `POST /runs/{id}/dataset` -> service writes image + extracts dims -> manifest updated
- **Auto-caption**: Browser -> `POST /runs/{id}/auto-caption` -> service reads each image, drives the captioner adapter, writes `captions/*.txt` + manifest
- **Train**: Browser -> `POST /runs/{id}/train` -> service flips status, schedules `BackgroundTasks` job -> trainer streams checkpoints/samples to B2 and progress into the manifest -> UI polls `GET /runs/{id}/progress`
- **Download / preview**: Browser -> `GET /runs/{id}/asset?key=...` -> service validates the key belongs to the run -> presigned URL

## Observability

- Structured JSON logging on all requests with `request_id`; request timing middleware
- `/metrics` (Prometheus format) and `/health` (B2 connectivity check)

## Canonical Files

- Run pipeline router: `services/api/app/runtime/runs.py`
- Run service orchestration: `services/api/app/service/runs.py`, `training.py`, `captioning.py`
- Run manifest store (repo layer): `services/api/app/repo/runs_store.py`
- Trainer adapter exemplar: `services/api/app/repo/trainer/simulated.py`
- Captioner adapter exemplar: `services/api/app/repo/captioner/templated.py`
- B2 S3 data access: `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/runs.py`
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Run pipeline tests: `services/api/tests/test_runs.py`
- Frontend API client / hooks: `apps/web/src/lib/api-client.ts`, `lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [LoRA Pipeline](docs/features/lora-pipeline.md)
- [Dataset Images](docs/features/dataset-images.md)
- [Captioning](docs/features/captioning.md)
- [Training](docs/features/training.md)
- [Sample Gallery](docs/features/sample-gallery.md)
- [LoRA Library](docs/features/lora-library.md)
- [Trainer & Captioner Providers](docs/features/trainer-providers.md)
- [Dashboard](docs/features/dashboard.md)
- [File Browser](docs/features/file-browser.md)
- [File Upload](docs/features/file-upload.md)
- [Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
