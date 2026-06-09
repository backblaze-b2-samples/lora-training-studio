<!-- last_verified: 2026-06-05 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

## 1. Repository Map

LoRA Training Studio is a browser-based LoRA fine-tuning workflow. Every
artifact — dataset images, captions, checkpoints, the final `.safetensors`,
and sample images — is persisted to Backblaze B2 under one prefix per run
(`lora-training/{run_id}/...`). Training runs a **real on-device SD 1.5 LoRA by
default** (`TRAINER_PROVIDER=local`; needs the ML stack + a GPU/MPS) — set
`TRAINER_PROVIDER=simulated` for a zero-config run with no GPU and no API keys.
See [ARCHITECTURE.md](ARCHITECTURE.md).

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/train/         New-run entry (name, token, base model, config)
  src/app/library/       LoRA Library — sample-scoped explorer + [runId] detail
  src/components/runs/   Run pipeline UI (stepper, dataset, captions, monitor, gallery)
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
  app/repo/runs_store.py     Manifest read/write + prefix-scoped run helpers
  app/repo/trainer/          Trainer adapters (local SD 1.5 default, simulated fallback, replicate stub)
  app/repo/captioner/        Captioner adapters (templated default, claude optional)
  app/service/{runs,captioning,training,runs_stats}.py
  app/runtime/runs.py        Run pipeline router
packages/shared/   Shared TypeScript types (mirror app/types/)
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

## 2. The Reusable B2 Base (do not strip)

This app is built on a starter kit's reusable B2 surface. Those pieces are kept
intact and are the foundation the LoRA pipeline builds on — do not strip,
rename, or replace them.

**Kept reusable surface**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **Full-bucket File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/`. The Files sidebar entry stays. This is the generic browse-everything view; the **LoRA Library** (`/library`) is the *sample-scoped* explorer that lists only runs under the `lora-training/` prefix.
- **Generic Upload.** `/upload` route and `apps/web/src/components/upload/`. The Upload sidebar entry stays. (Per-run dataset upload is a separate, sample-specific flow under `components/runs/`.)
- **Layered B2 data access.** `repo/b2_client.py` S3 helpers are reused verbatim by the run/training services. boto3 stays contained in `repo/`.

**App-specific surface (this is the point of the app)**
- **Dashboard.** `/` and `apps/web/src/components/dashboard/` are rewritten for training metrics + a B2 storage breakdown by artifact type. New aggregations flow through `runtime -> service -> repo` and are exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`.
- **Run pipeline.** Train (`/train`), Library (`/library`, `/library/[runId]`), and `components/runs/` implement the dataset → captions → training → samples → download state machine.
- Update the relevant `docs/features/*.md` in the same PR as any change (see §9).

**Trainer & Captioner adapter invariant**
- External training/captioning SDKs are contained the same way `boto3` is: `anthropic` (Claude captioner), `replicate` (cloud trainer), and the **local trainer's ML stack** (`torch`/`diffusers`/`transformers`/`peft`/`torchvision`, in `repo/trainer/local.py` + `_sd_lora.py`) are imported **lazily, only inside their `repo/` adapters** (`repo/trainer/`, `repo/captioner/`) — `local`'s stack loads inside `train()`, so importing the package never pulls in torch and a fresh `pnpm dev` still *starts* with no GPU or keys. The **default** trainer is `local` (real SD 1.5 LoRA): running a training job needs `pip install -r services/api/requirements-local-trainer.txt` and a GPU/MPS. `SimulatedTrainer` + `TemplatedCaptioner` need none of the optional deps and are the zero-config fallback (`TRAINER_PROVIDER=simulated`). This is mechanically enforced (see §5).

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3`, `anthropic`, `replicate`, or the local-trainer ML stack (`torch`/`diffusers`/`transformers`/`peft`/`torchvision`) outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters; optional SDKs imported lazily inside the adapter
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No external SDK (boto3/anthropic/replicate + torch/diffusers/transformers/peft) outside repo/ | `tests/test_structure.py::test_external_sdks_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
