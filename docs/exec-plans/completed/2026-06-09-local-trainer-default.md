# Plan: Make the local (real) trainer the default

## Goal

Flip the default `TRAINER_PROVIDER` from `simulated` to `local` so a run uses
the real on-device Stable Diffusion 1.5 LoRA trainer out of the box. `simulated`
remains an explicit, opt-in zero-config fallback (`TRAINER_PROVIDER=simulated`)
for no-GPU machines, CI, and demos. This reverses the constraint in
`2026-06-08-local-sd15-trainer.md` ("the default stays `simulated`").

## Why

User request: the real local trainer should be the default; the simulated
("stubbed") run should no longer be what you get unless explicitly selected.

## Change

One canonical switch plus doc/UX alignment:

- `services/api/app/config/settings.py` — `trainer_provider` default `"simulated"` -> `"local"` (and the factory fallback in `repo/trainer/__init__.py`).
- `services/api/app/types/runs.py` + `apps/web/src/app/train/page.tsx` — default `base_model` `sdxl-base-1.0` -> `sd-1.5` (the model the local trainer actually fine-tunes; `base_model` is a display label only).
- Docs/UX reworded so `local` is the default and `simulated` is the opt-in fallback: `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `.env.example`, `docs/features/training.md`, `docs/features/trainer-providers.md`, the trainer adapter docstrings (`base.py`, `simulated.py`, `local.py`, `_sd_lora.py`, `replicate.py`, `trainer/__init__.py`), the `train` page copy, and `infra/railway/README.md`.

## Consequences (called out, not blockers)

- **`pnpm dev` is no longer zero-dependency for a training run.** Imports stay
  lazy, so the server still *starts* with no GPU/keys, but starting a run now
  requires `pip install -r services/api/requirements-local-trainer.txt` and a
  GPU/MPS backend — or `TRAINER_PROVIDER=simulated`.
- **Railway (no GPU):** `infra/railway/README.md` now instructs setting
  `TRAINER_PROVIDER=simulated` there, since the Railway build doesn't install
  the ML stack and the platform has no GPU.
- **Tests:** `tests/test_runs.py` exercised the *default* trainer end-to-end;
  the `fake_b2` fixture now pins `TRAINER_PROVIDER=simulated` so that hermetic,
  zero-dependency path is preserved regardless of the default.

## Verification

- `pnpm lint:api && pnpm test:api && pnpm check:structure` green.
- `pnpm lint && pnpm build` (frontend) green.
- A real `local` run remains verified manually per
  `docs/features/trainer-providers.md` (multi-minute GPU/MPS job).
