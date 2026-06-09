<!-- last_verified: 2026-06-08 -->
# Feature: Trainer & Captioner Providers

## Purpose
The adapter pattern that keeps training and captioning pluggable: a zero-config default plus optional, clearly-marked real/cloud/vision extensions — with the external SDKs contained in `repo/`.

## Used By
- API (indirectly): training and captioning services select an adapter per run
- Config: `settings.trainer_provider`, `settings.captioner_provider`

## Core Functions
- `services/api/app/repo/trainer/__init__.py` — `get_trainer()` factory
- `services/api/app/repo/trainer/base.py` — `Trainer` protocol, `TrainerStep`, `TrainerResult`
- `services/api/app/repo/trainer/simulated.py` — default, no GPU/keys
- `services/api/app/repo/trainer/local.py` — optional **real** trainer: SD 1.5 LoRA on-device (MPS/CUDA)
- `services/api/app/repo/trainer/_sd_lora.py` — diffusers + peft training internals for `local`
- `services/api/app/repo/trainer/replicate.py` — optional extension stub (not wired)
- `services/api/app/repo/captioner/__init__.py` — `get_captioner()` factory
- `services/api/app/repo/captioner/templated.py` — default, offline
- `services/api/app/repo/captioner/claude.py` — optional, Claude vision

## Canonical Files
- Trainer factory + protocol: `services/api/app/repo/trainer/`
- Captioner factory + protocol: `services/api/app/repo/captioner/`

## Inputs
- `TRAINER_PROVIDER` (default `simulated`; `local` for real on-device SD 1.5; `replicate` for the stub), `REPLICATE_API_TOKEN`
- `local`-only: `LOCAL_SD_MODEL_ID` (default `stable-diffusion-v1-5/stable-diffusion-v1-5`), `LOCAL_TRAIN_RESOLUTION` (512), `LOCAL_MILESTONES` (4), `LOCAL_SAMPLES_PER_MILESTONE` (4) — requires `pip install -r requirements-local-trainer.txt`
- `CAPTIONER_PROVIDER` (default `templated`; `claude`), `ANTHROPIC_API_KEY`, `CLAUDE_CAPTION_MODEL` (`claude-haiku-4-5`)

## Outputs
- A `Trainer` / `Captioner` instance honoring its protocol

## Flow
- The service calls `get_trainer()` / `get_captioner()`; the factory returns the default unless a provider is configured
- Optional adapters import their SDK (`replicate`, `anthropic`) and the local-trainer ML stack (`torch`/`diffusers`/`peft`, via `_sd_lora`) **lazily inside the adapter**, so importing the package never requires the dependency or a key
- `SimulatedTrainer` emits placeholder checkpoints, a stub `.safetensors`, Pillow samples, and a synthetic loss curve
- `LocalTrainer` fine-tunes a real SD 1.5 UNet LoRA with diffusers + peft on the Metal (MPS) / CUDA backend: it reads the dataset images + captions from B2, trains in fp32 (mandatory on MPS), and writes real checkpoints, real generated samples, and a real `.safetensors` — identical B2 layout to the simulated trainer. Training is a multi-minute job; the first run downloads the ~4 GB base model.
- `ReplicateTrainer` is an extension stub: it implements the interface but `train()` raises `NotImplementedError`

## Edge Cases
- `replicate` selected without token → runtime error
- `claude` selected without `ANTHROPIC_API_KEY` → runtime error
- `local` selected without the ML deps installed → `ImportError` when `train()` runs (lazy import); install `requirements-local-trainer.txt`
- `local` with no dataset images on B2 → `RuntimeError` (raised before model load)
- Importing an optional adapter without its SDK installed → fine until `train()`/`caption()` is called (lazy import)

## UX States
- Not applicable (backend selection)

## Verification
- Test files: `services/api/tests/test_runs.py` (default trainer/captioner exercised end-to-end), `tests/test_structure.py::test_external_sdks_only_in_repo`
- Required cases: default path completes a run; SDK containment enforced
- Quick verify command: `pnpm check:structure`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, structural test enforces SDK containment

## Related Docs
- [Training](training.md)
- [Captioning](captioning.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
