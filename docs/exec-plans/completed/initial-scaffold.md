# Scaffold plan — `lora-training-studio`

Derived from `vibe-coding-starter-kit` (cloned fresh at HEAD `8fc490f`).
Source of truth for the delta: `.claude/scratch/vcsk-264c379d-32b8-4a4b-bc37-c563ab6b59a2/`.

> **Build target:** `./lora-training-studio` (i.e. `sampleapps/.local/lora-training-studio`, a sibling of the three existing samples). Gitignored; published later as its own repo.

---

## Decisions locked from the user's open questions

| Question | Decision | Consequence |
|---|---|---|
| Cloud-only vs local-GPU training? | **Provider adapter, simulated by default** | `pnpm dev` runs on a stock **Mac with no GPU and no API keys** — the `SimulatedTrainer` emits placeholder checkpoints, a stub `.safetensors`, and Pillow-rendered sample images, with a synthetic loss curve over time. Real cloud training (Replicate/FAL) is an optional, clearly-marked repo-layer extension point. *(This directly answers the user's "would this run on my Mac?" — yes.)* |
| Publish flow? | **Download / B2 only** | Final LoRA is downloadable via a B2 presigned `.safetensors` URL. **No** Hugging Face / Civitai integration. (HF push noted only as a future extension.) |
| Captioning? | **Manual editor + optional auto-caption** | Per-image caption editor always available. "Auto-caption all" works offline via a `TemplatedCaptioner` (default) and via Claude vision when `ANTHROPIC_API_KEY` is set (`ClaudeCaptioner`, optional). Captions versioned on B2 next to the dataset. |

**Net effect on the demo:** zero-config, runs anywhere, and the *whole point* — dataset → captions → intermediate checkpoints → final LoRA → sample gallery, all persisted and addressable on B2 — is fully exercised without any paid GPU.

---

## 1. Purpose

`LoRA Training Studio` is an end-to-end, browser-based LoRA fine-tuning workflow for image models. A practitioner uploads a handful of training images, captions them (by hand or with an optional vision model), configures and launches a training run, watches the loss curve and intermediate sample gallery fill in, and finally downloads the trained `.safetensors` LoRA. Every artifact in that lifecycle — the source dataset, the per-image captions, each intermediate checkpoint, the final LoRA, and every sample-gallery image — is written to and read back from **Backblaze B2** over the S3-compatible API, keyed under one prefix per run. It is for ML practitioners and tool-builders evaluating B2 as the artifact store behind a training UI (a "Kohya alternative" / "Civitai trainer"-style experience), and for the Tier-1 program as a data-heavy B2 demo that cross-promotes the HF / DVC / W&B integration tracks. The training engine is intentionally pluggable and simulated-by-default so the sample runs out of the box; the B2 storage layer is the real, production-shaped part.

> **"Versioned on B2" means keyed/immutable retention**, not S3 bucket versioning: every run, every checkpoint step, and every sample set is retained as a distinct, addressable object under `lora-training/{run_id}/...`. No bucket-level S3 versioning is enabled (keeps us inside the S3-default standard, no b2-native calls).

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. We **keep** its full reusable B2 surface (per AGENTS.md §2 — non-negotiable), **trim** almost nothing (the kit is already lean; PDF/audio metadata is retained as reusable infra rather than ripped out — see note), and **add** the runs/training pipeline + a scoped library explorer.

### KEEP (as-is or naming-only edits)

| Area | Why |
|---|---|
| UI kit `apps/web/src/components/ui/**` + design tokens in `globals.css` + `/design` page | Starter contract — never edit generated shadcn files; restyle via tokens only. |
| **`/upload` page + `components/upload/**`** | Starter contract — generic B2 upload surface. (The per-run dataset upload is a *separate* sample-specific flow, see ADD.) |
| **`/files` full-bucket explorer** (`app/files/`, `components/files/**`, `lib/file-tree.ts`) + its **Files** sidebar entry | **Non-negotiable keep** — full-bucket browse stays exactly as shipped. |
| `/settings` page + `components/settings/**` | Generic settings + danger zone. |
| Sidebar shell, header, theme provider, command palette, health banner | Layout scaffolding. |
| Layered FastAPI backbone: `types → config → repo → service → runtime`, `main.py`, structural tests, JSON logging, `/health`, `/metrics` | The architectural invariants and mechanical enforcement we build *within*. |
| `repo/b2_client.py` S3 helpers (`upload_file`, `list_files`, `get_file_metadata`, `delete_file`, `get_presigned_url`, `get_upload_stats`, `check_connectivity`) | Reused verbatim by the new run/training services. boto3 stays contained here. |
| Metadata extraction (`service/metadata.py`, `Pillow`, image dims/EXIF) | **Reused** to extract dimensions on dataset images. PDF/audio extraction (`PyPDF2`) is retained as generic infra — *deliberately not trimmed* to avoid destabilizing the green metadata tests; called out here so it isn't read as drift. |
| `packages/shared` type-mirroring pattern, TanStack Query data layer (`lib/queries.ts`, `lib/api-client.ts`), `scripts/{dev.sh,doctor.mjs,pick-port.mjs}`, `infra/railway/`, e2e harness | Reused; extended, not replaced. |

### TRIM (remove / replace)

| Item | Action | Why |
|---|---|---|
| `docs/images/b2-starterkit-dashboard1.png`, `b2-starterkit-fileview2.png` | **Delete**; README "What it looks like" section becomes a "screenshots added on publish" placeholder | They depict the starter UI, not this app — misleading. New screenshots are created later via the `sample-screenshotter` skill (binary-asset creation is out of scope here). |
| Default dashboard components (`components/dashboard/{stats-cards,upload-chart,recent-uploads-table}.tsx`) | **Replace** with training-specific versions (see ADD / §5) | AGENTS.md §2: the dashboard is the one screen meant to be rewritten per app. |
| `docs/features/dashboard.md` | **Rewrite** for training metrics | Same-PR doc rule. |
| Starter naming / `b2ai-oss-start` tag everywhere | **Rename** (see §6) | New sample identity + per-sample user-agent/UTM. |
| `B2_KEY_ID` env var + `b2_key_id` field | **Rename** to `B2_APPLICATION_KEY_ID` / `b2_application_key_id`; **add** `B2_REGION` | Parent CLAUDE.md Standard #3 (see §3 note). |

### ADD (new for `lora-training-studio`)

**Frontend**
- `app/train/page.tsx` — thin "**New run**" entry: name, instance token (e.g. `sks dog`), base-model select (label only), training config (steps / rank / LR) → `POST /runs` → redirect to the run detail.
- `app/library/page.tsx` — **LoRA Library**: the **sample-scoped asset explorer** (the required per-sample explorer), listing all runs under the `lora-training/` prefix as cards.
- `app/library/[runId]/page.tsx` — **run detail / pipeline view**: the canonical per-run surface (stepper + per-stage actions).
- `components/runs/**` — `run-grid.tsx`, `run-detail.tsx`, `pipeline-stepper.tsx`, `dataset-grid.tsx` (thumbnails + add/remove), `caption-editor.tsx`, `training-monitor.tsx` (step progress + Recharts loss curve), `sample-gallery.tsx`, `lora-download-card.tsx`, `run-status-badge.tsx`.
- `components/dashboard/**` — rewritten `stats-cards.tsx`, `storage-breakdown.tsx` (B2 storage by artifact type — the "heavy across the lifecycle" story), `recent-runs-table.tsx`.
- Sidebar: add **Train** (`/train`) and **Library** (`/library`) nav entries above the kept Upload / Files. Title "OSS Starter Kit" → "LoRA Training Studio".
- `lib/queries.ts` / `lib/api-client.ts` hooks: `useRuns`, `useRun`, `useCreateRun`, `useUploadDatasetImages`, `useDeleteDatasetImage`, `useCaptions`, `useAutoCaption`, `useStartTraining`, `useRunProgress` (polls via `refetchInterval` while `status === "training"`), `useDeleteRun`, `useRunsStats`, `useRunAssetUrl` (presigned thumbnails / samples / LoRA download).
- `packages/shared/src/types.ts`: add `RunStatus`, `RunConfig`, `RunSummary`, `RunDetail`, `StageState`, `TrainingProgress`, `DatasetImage`, `Caption`, `SampleImage`, `StorageBreakdown`.

**Backend (within the layering)**
- `types/runs.py` — Pydantic models mirroring the shared TS types; `RunStatus` enum: `created → captioning → ready_to_train → training → sampling → complete` (+ `failed`).
- `repo/runs_store.py` — manifest read/write (`lora-training/{run_id}/run.json`), prefix-scoped list/delete (built on the existing S3 helpers; boto3 stays in `repo/`).
- `repo/trainer/` — `base.py` (`Trainer` protocol: drive training, emit step progress + checkpoints + samples), `simulated.py` (**default**, no creds), `replicate.py` (**optional extension stub**, behind `REPLICATE_API_TOKEN`; interface implemented, clearly marked not-wired). Selected in `config`.
- `repo/captioner/` — `base.py` (`Captioner` protocol), `templated.py` (**default**, offline), `claude.py` (**optional**, Anthropic Messages API vision behind `ANTHROPIC_API_KEY`; lazy `import anthropic`; model `claude-haiku-4-5`).
- `service/runs.py` — run CRUD + dataset image add/remove + manifest orchestration.
- `service/captioning.py` — manual set + auto-caption (drives captioner adapter).
- `service/training.py` — orchestrates a run via `BackgroundTasks` (same pattern as the avatar/dubbing siblings): drives the trainer, writes progress to the manifest and checkpoints/samples to B2 as steps complete, transitions status.
- `runtime/runs.py` — router (see §3 for the endpoint list). Registered in `main.py`; add `PUT` to CORS `allow_methods`.

**Layering note:** the "no external SDK outside `repo/`" invariant is *extended*, not broken — `boto3` stays repo-only (structural test still green), and the new `anthropic` / `replicate` SDKs are imported **only** inside their `repo/` adapters (lazy). I'll add a structural-test assertion (or extend the existing `test_boto3_only_in_repo`) so this is mechanically enforced.

**B2 prefix layout (one run = one prefix):**
```
lora-training/{run_id}/
  run.json                         # manifest: status, config, metrics, artifact keys + sizes
  dataset/{image_id}.{ext}         # uploaded training images
  captions/{image_id}.txt          # one caption per image (versioned alongside)
  checkpoints/step-{NNNNNN}.bin    # intermediate checkpoints (heavy)
  lora/{run_id}.safetensors        # final downloadable LoRA
  samples/step-{NNNNNN}/sample-{NN}.png  # sample gallery per checkpoint step
  samples/final/sample-{NN}.png
```

---

## 3. B2 surface (S3 operations)

All S3-compatible, all through `repo/b2_client.py`. **No b2-native API anywhere.**

| Operation | S3 call | Used for |
|---|---|---|
| Write dataset image / caption / checkpoint / LoRA / sample / manifest | `put_object` | every artifact write |
| List runs (scoped) + full-bucket browse + per-run assets | `list_objects_v2` (paginated via `ContinuationToken`) | Library, `/files`, dashboard stats, per-run asset listing |
| Object metadata | `head_object` | dataset image dims, manifest sanity |
| Delete image / delete whole run prefix | `delete_object` (loop over listed keys) | remove image, delete run |
| Download LoRA / view thumbnails & samples | `generate_presigned_url` (attachment for LoRA; inline for images, 10-min expiry) | downloads + previews |
| Bucket connectivity | `head_bucket` | `/health` |

**Standard #3 compliance (important):** parent `../CLAUDE.md` mandates `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, `B2_ENDPOINT`. The starter ships `B2_KEY_ID` and **no** region; this sample renames to `B2_APPLICATION_KEY_ID` and **adds** `B2_REGION` (passed to boto3 as `region_name`). ⚠️ **Divergence note:** the three sibling samples kept the starter's `B2_KEY_ID`. We follow the *documented* standard (audited by `/b2-doctor` and the reviewer), not the siblings' practice. **Standard #2:** the single `get_s3_client()` already sets `user_agent_extra`; value becomes `b2ai-lora-training-studio`. **Standard #1:** S3 is the only API — satisfied.

---

## 4. Key features (seed README + `docs/features/` stubs)

1. **Guided LoRA pipeline** — create a run, then move through dataset → captions → training → samples → download as a single tracked state machine.
2. **Dataset images on B2** — per-run drag-and-drop image upload with thumbnails, dimension extraction, add/remove.
3. **Captioning** — per-image manual editor + optional one-click auto-caption (offline templated default, Claude vision when configured); captions stored beside the dataset.
4. **Training with live monitoring** — simulated-by-default trainer streams step progress, a loss curve, intermediate checkpoints, and a growing sample gallery — all written to B2.
5. **LoRA Library (scoped explorer)** — browse every run scoped to the `lora-training/` prefix; open a run to view its full artifact set and download the `.safetensors`.
6. **Storage-lifecycle dashboard** — runs, LoRAs produced, training-image count, and a B2 storage breakdown by artifact type.

---

## 5. Doc transforms

| Starter doc | Action |
|---|---|
| `README.md` | **Rewrite** hero/features/quickstart for LoRA Training Studio; new clone URL `backblaze-b2-samples/lora-training-studio`; env steps for `B2_APPLICATION_KEY_ID` + `B2_REGION` (+ optional `REPLICATE_API_TOKEN`, `ANTHROPIC_API_KEY` as clearly-optional); UTM → `b2ai-lora-training-studio`; "What it looks like" → screenshots-on-publish placeholder. |
| `AGENTS.md` | **Rewrite** repo map + surface to this app; keep invariants/layering/commands/enforcement; reframe §2 "keep UI kit/Files/Upload" as the reusable B2 base this app builds on; document the trainer/captioner adapter invariant. |
| `ARCHITECTURE.md` | **Rewrite** components, data flows (run lifecycle), B2 prefix layout, canonical files; keep layering rules. |
| `docs/features/dashboard.md` | **Rewrite** (training metrics + storage breakdown). |
| `docs/features/file-browser.md`, `file-upload.md` | **Keep** (naming-only edits). |
| `docs/features/metadata-extraction.md` | **Keep**, light reframe (image-focused for dataset images). |
| `docs/features/_template.md` | **Keep** unchanged. |
| `docs/{design-system,SECURITY,RELIABILITY}.md`, `docs/{app-workflows,dev-workflows}.md` | **Keep**; edit naming + `B2_KEY_ID`→`B2_APPLICATION_KEY_ID` (SECURITY); rewrite user journeys in app-workflows for the pipeline. |
| `docs/exec-plans/**` | Keep structure. This plan lands at `docs/exec-plans/completed/initial-scaffold.md` in Phase 5. |
| **New** `docs/features/lora-pipeline.md` | Stub — the end-to-end state machine. |
| **New** `docs/features/dataset-images.md` | Stub — per-run image upload. |
| **New** `docs/features/captioning.md` | Stub — manual + optional auto-caption. |
| **New** `docs/features/training.md` | Stub — trainer adapter, simulated default, progress/loss/checkpoints. |
| **New** `docs/features/sample-gallery.md` | Stub — sample image generation + presigned viewing. |
| **New** `docs/features/lora-library.md` | Stub — the scoped explorer + run detail + download. |
| **New** `docs/features/trainer-providers.md` | Stub — adapter pattern (Simulated default, optional Replicate; templated vs Claude captioner). |

All new docs follow `docs/features/_template.md` and carry a `last_verified:` line.

---

## 6. Rename table

Sweep `vibe-coding-starter-kit` (16 files) → `lora-training-studio` and the title-case forms → `LoRA Training Studio`. Concrete identifiers:

| From | To | Locations |
|---|---|---|
| `vibe-coding-starter-kit` (kebab) | `lora-training-studio` | root `package.json` name; clone URLs in `README.md` |
| `@vibe-coding-starter-kit/web` | `@lora-training-studio/web` | `apps/web/package.json` name; root `package.json` pnpm `--filter` (dev:web, build, typecheck, lint, test:e2e); README e2e command |
| `@vibe-coding-starter-kit/shared` | `@lora-training-studio/shared` | `packages/shared/package.json`; TS imports in `lib/{queries,api-client,file-tree}.ts`, `components/upload/upload-progress.tsx`, `components/layout/command-palette.tsx`, `components/files/{file-preview,file-metadata-panel,file-browser}.tsx`; `next.config.ts` |
| `Vibe Coding Starter Kit` / `OSS Starter Kit` (title) | `LoRA Training Studio` | `README.md` H1; `app-sidebar.tsx` header label; `main.py` FastAPI `title`; AGENTS.md / ARCHITECTURE.md headers; command-palette label |
| `user_agent_extra="b2ai-oss-start"` | `user_agent_extra="b2ai-lora-training-studio"` | `repo/b2_client.py:45` |
| `utm_content=b2ai-oss-start` | `utm_content=b2ai-lora-training-studio` | `README.md` (×3), `scripts/doctor.mjs:187`, `app-sidebar.tsx:110` |
| `B2_KEY_ID` (env) / `b2_key_id` (field) | `B2_APPLICATION_KEY_ID` / `b2_application_key_id` | `.env.example`, `settings.py:6`, `main.py:31` (REQUIRED_B2_SETTINGS), `scripts/doctor.mjs:32`, `infra/railway/README.md:28`, `docs/SECURITY.md:9`, `README.md:124`, `repo/b2_client.py:41` |
| *(add)* `B2_REGION` / `b2_region` (`region_name`) | new | `.env.example`, `settings.py`, `main.py` (REQUIRED_B2_SETTINGS), `scripts/doctor.mjs`, `infra/railway/README.md`, `README.md`, `repo/b2_client.py` (`region_name=settings.b2_region`) |
| *(update placeholders)* | match new var names | `main.py` `PLACEHOLDER_VALUES`, `.env.example` example block |
| pnpm-lock.yaml workspace name (1 ref) | reconciles on first `pnpm install` | note in next-steps |

No `name` field exists in `services/api/pyproject.toml` — nothing to rename there. No Docker image tags / GitHub workflow files ship in the starter (Railway is the only deploy target, env-table only).

`.env.example` final shape:
```
# Backblaze B2 (required)
B2_ENDPOINT=your_b2_endpoint
B2_REGION=your_b2_region
B2_APPLICATION_KEY_ID=your_application_key_id
B2_APPLICATION_KEY=your_application_key
B2_BUCKET_NAME=your-bucket-name

# Optional — real cloud training (default trainer is simulated, needs neither)
# REPLICATE_API_TOKEN=your_replicate_token
# Optional — auto-caption via Claude vision (default is offline templated captions)
# ANTHROPIC_API_KEY=your_anthropic_key
```

---

## Out of scope / future extension points (noted, not built)

- Real cloud training (Replicate/FAL) — adapter stub only.
- HF / Civitai publish — user chose B2-only.
- W&B run/loss tracking (#61), DVC dataset versioning (#49), HF Transformers (#67) — natural cross-promo hooks for later.
- S3 bucket versioning — out (stay S3-default; keyed retention instead).

## Standards self-check (pre-empting `/b2-doctor` + reviewer)

- ✅ **S3-only** — no b2-native calls.
- ✅ **Custom user agent** — `b2ai-lora-training-studio` on the single shared S3 client.
- ✅ **Standardized `B2_*` names** — `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, `B2_ENDPOINT`.
- ✅ **Bucket explorer kept** (`/files`) **+ scoped explorer added** (`/library`).
- ✅ Layering preserved; external SDKs contained in `repo/`.
