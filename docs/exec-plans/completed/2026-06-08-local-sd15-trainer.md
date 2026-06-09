# Plan: Real local LoRA training (SD 1.5 on Apple Silicon / MPS)

> **Superseded in part (2026-06-09):** the "default stays `simulated`" decision
> below was later reversed — `local` is now the default trainer
> (`TRAINER_PROVIDER=local`), with `simulated` as the opt-in zero-config
> fallback. See `2026-06-09-local-trainer-default.md`. The rest of this plan
> (the trainer implementation) still stands.

## Goal

Add a real, opt-in trainer that actually fine-tunes a LoRA on the user's
machine — replacing the simulated placeholder output with genuine trained
`.safetensors` weights and real generated sample images, all still persisted
to B2 exactly as before. Target Stable Diffusion 1.5 via `diffusers` + `peft`
on the Metal (MPS) backend. The default stays `simulated`; this is behind
`TRAINER_PROVIDER=local`.

FLUX was evaluated and is feasible on the M4 Max (36 GB) via `mflux`/MLX but
marginal (~34 GB download, ~15–25 s/step, subprocess integration). SD 1.5 is
the realistic first cut: ~4 GB model, seconds-to-low-minutes per run, clean
in-process fit to the synchronous `Trainer.train()` + `on_progress` contract.
A `provider="mflux"` FLUX adapter can follow as phase 2.

## Constraints learned (Apple Silicon / MPS)

- **fp32 only** on MPS — fp16 yields NaN loss, bf16 is blocked. All modules
  load in `torch.float32`.
- **No bitsandbytes / xformers** (CUDA-only). We train only the small LoRA
  adapter params, so full-precision optimizer state is cheap.
- SD 1.5 in fp32 (UNet ~3.4 GB + VAE + text encoder + activations) fits the
  36 GB budget comfortably at batch size 1, 512px.

## Scope

- New `repo/trainer/local.py` — `LocalTrainer` implementing the `Trainer`
  protocol. Heavy ML libs imported **lazily inside the adapter** (same rule as
  `replicate.py`), so a fresh clone with the default trainer needs none of them.
- Helper module `repo/trainer/_sd_lora.py` if `local.py` would exceed the
  300-line limit (model load / train step / sampling / save split out).
- `config/settings.py`: add `local_sd_model_id` (default the canonical SD 1.5
  re-host), `local_train_resolution` (512), `local_milestones` (4),
  `local_samples_per_milestone` (mirror the simulated cadence so B2 object
  counts stay bounded and the UI is consistent).
- `requirements.txt`: add `torch`, `torchvision`, `diffusers`, `transformers`,
  `peft`, `accelerate`, `safetensors` under a clearly-marked optional block.
- `tests/test_structure.py`: extend `CONTAINED_SDKS` with the new ML libs so
  they're mechanically forbidden outside `repo/`.
- Captioning: enable the existing Claude captioner via env (`CAPTIONER_PROVIDER=
  claude` + `ANTHROPIC_API_KEY`). No code change; document the two-line setup.
- Docs: update `docs/features/training.md`, `docs/features/trainer-providers.md`,
  `ARCHITECTURE.md` (External Services), `README.md` optional-deps note, and the
  AGENTS.md mechanical-enforcement table.

## Trainer design (maps onto the existing contract)

`train(run_id, instance_token, total_steps, rank, learning_rate, dataset_keys,
on_progress) -> TrainerResult`:

1. **Fetch inputs from B2** (`get_object_bytes`): each dataset image; the
   matching caption at `lora-training/{run_id}/captions/{image_id}.txt`
   (image_id = key stem). Fall back to `"a photo of {instance_token}"` if a
   caption is missing.
2. **Load SD 1.5** (`StableDiffusionPipeline.from_pretrained`, `safety_checker=
   None`), extract tokenizer/text_encoder/vae/unet + a `DDPMScheduler` for
   training. Freeze base; add a `peft` `LoraConfig` (rank from config, targets
   `to_q/to_k/to_v/to_out.0`) to the UNet. Move all to `mps`, fp32.
3. **Train loop** (`AdamW` on LoRA params, batch 1): encode image→latents
   (×scaling_factor), sample noise + timestep, predict, MSE vs noise (or
   velocity for v-pred), backward, step.
4. **Progress cadence**: log a loss point every ~`total_steps/20` steps
   (`on_progress` with loss only). At each of `local_milestones` milestones:
   save an intermediate LoRA checkpoint (`checkpoints/step-NNNNNN.bin` via
   `torch.save`), generate `local_samples_per_milestone` real images with the
   current pipeline → upload PNGs → `on_progress` with checkpoint + sample keys.
5. **Finish**: write the final `.safetensors`
   (`StableDiffusionPipeline.save_lora_weights`) to a temp dir, upload bytes to
   `lora/{run_id}.safetensors`; render the final sample set; return
   `TrainerResult(lora_key, final_sample_keys)`.

The service layer (`service/training.py`) and B2 key layout are unchanged — the
adapter is a drop-in swap for `SimulatedTrainer`.

## Steps

1. Install deps into the venv; verify `torch.backends.mps.is_available()`.
2. Extend `CONTAINED_SDKS`; confirm structure test still passes (imports live
   in `repo/`).
3. Add settings fields.
4. Implement `LocalTrainer` (+ helper module if needed), lazy imports.
5. Wire `local` into `repo/trainer/__init__.py` factory.
6. Add an integration smoke test that monkeypatches B2 + a tiny fake model path
   OR is skipped unless `RUN_LOCAL_TRAINER_TEST=1` (real training is too heavy
   for CI). Keep the structural/contract tests green.
7. Manual end-to-end: real run over `.local/datasets/` images → verify a real
   `.safetensors` + real samples land under the run prefix on B2 and the UI
   loss curve / gallery / download work.
8. Update docs in the same change; move this plan to `completed/`.

## Risks / notes

- Real training is a multi-minute blocking `BackgroundTasks` job (vs ~30 s
  simulated). Acceptable for single-user local; document it.
- First run downloads ~4 GB (SD 1.5) from HF Hub; cached thereafter.
- Keep `local.py` (+ helper) each under 300 lines.
- ~~Do **not** change the default provider — `simulated` stays the zero-config
  default so `pnpm dev` runs with no GPU and no keys.~~ **Reversed 2026-06-09:**
  `local` is now the default; `simulated` is the opt-in fallback. See
  `2026-06-09-local-trainer-default.md`.
