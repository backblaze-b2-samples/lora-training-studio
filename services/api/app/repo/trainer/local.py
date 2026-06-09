"""Real on-device LoRA trainer — Stable Diffusion 1.5 via diffusers + peft.

Opt-in via `TRAINER_PROVIDER=local`. Unlike `SimulatedTrainer`, this fine-tunes
a genuine LoRA and writes real `.safetensors` weights and real generated sample
images to B2 — the storage layout is identical, so it is a drop-in swap for the
simulated trainer behind the same `Trainer` contract.

The heavy ML stack lives in `_sd_lora` and is imported **lazily inside
`train()`** (mirroring how `replicate.py` defers its SDK), so importing this
adapter — or running the default simulated path — never loads torch.

Target hardware is Apple Silicon (MPS); see `_sd_lora` for the fp32 constraint.
Training is a multi-minute, CPU/GPU-bound `BackgroundTasks` job and the first
run downloads the ~4 GB base model from HuggingFace.
"""

import logging

from app.config import settings
from app.repo.b2_client import get_object_bytes, put_object_bytes
from app.repo.runs_store import caption_key, checkpoint_key, lora_key, sample_key
from app.repo.trainer.base import ProgressCallback, TrainerResult, TrainerStep

logger = logging.getLogger(__name__)


def _ids_from_dataset_key(key: str) -> tuple[str, str] | None:
    """Split `lora-training/{run_id}/dataset/{image_id}.{ext}` -> (run_id, image_id)."""
    head, _, tail = key.partition("/dataset/")
    if not tail:
        return None
    run_id = head.rsplit("/", 1)[-1]
    image_id = tail.rsplit(".", 1)[0]
    return run_id, image_id


class LocalTrainer:
    name = "local"

    def train(
        self,
        run_id: str,
        instance_token: str,
        total_steps: int,
        rank: int,
        learning_rate: float,
        dataset_keys: list[str],
        on_progress: ProgressCallback,
    ) -> TrainerResult:
        # Lazy import: the ML stack is only pulled in on this opt-in path.
        from app.repo.trainer import _sd_lora

        items = self._load_dataset(run_id, instance_token, dataset_keys)
        if not items:
            raise RuntimeError(
                f"No dataset images found on B2 for run {run_id}; cannot train."
            )

        logger.info(
            "Loading base model %s for run_id=%s (%d images, %d steps)",
            settings.local_sd_model_id,
            run_id,
            len(items),
            total_steps,
        )
        engine = _sd_lora.load_engine(
            settings.local_sd_model_id,
            rank,
            learning_rate,
            settings.local_train_resolution,
        )
        examples = _sd_lora.prepare_examples(engine, items)

        milestones = self._milestones(total_steps)
        log_every = max(1, total_steps // 20)
        prompt = f"a photo of {instance_token.strip() or 'sks'}"

        for step in range(1, total_steps + 1):
            loss = _sd_lora.train_step(engine, examples[(step - 1) % len(examples)])

            if step in milestones:
                ckpt_key = checkpoint_key(run_id, step)
                put_object_bytes(
                    ckpt_key,
                    _sd_lora.lora_checkpoint_bytes(engine),
                    "application/octet-stream",
                )
                sample_keys = self._emit_samples(
                    _sd_lora, engine, run_id, step, prompt
                )
                on_progress(
                    TrainerStep(
                        step=step,
                        total_steps=total_steps,
                        loss=loss,
                        checkpoint_key=ckpt_key,
                        sample_keys=sample_keys,
                        message=f"Checkpoint at step {step}",
                    )
                )
            elif step % log_every == 0:
                on_progress(
                    TrainerStep(
                        step=step,
                        total_steps=total_steps,
                        loss=loss,
                        message=f"Step {step}/{total_steps}",
                    )
                )

        final_samples = self._emit_samples(_sd_lora, engine, run_id, None, prompt)
        final_lora_key = lora_key(run_id)
        put_object_bytes(
            final_lora_key,
            _sd_lora.lora_safetensors_bytes(engine),
            "application/octet-stream",
        )
        logger.info("Local training complete for run_id=%s", run_id)
        return TrainerResult(
            lora_key=final_lora_key, final_sample_keys=final_samples
        )

    def _load_dataset(
        self, run_id: str, instance_token: str, dataset_keys: list[str]
    ) -> list[tuple[bytes, str]]:
        """Fetch each dataset image and its caption from B2."""
        items: list[tuple[bytes, str]] = []
        fallback = f"a photo of {instance_token.strip() or 'sks'}"
        for key in dataset_keys:
            image_bytes = get_object_bytes(key)
            if image_bytes is None:
                logger.warning("Dataset image missing on B2: %s", key)
                continue
            ids = _ids_from_dataset_key(key)
            caption = fallback
            if ids is not None:
                cap = get_object_bytes(caption_key(*ids))
                if cap is not None and cap.strip():
                    caption = cap.decode("utf-8").strip()
            items.append((image_bytes, caption))
        return items

    def _emit_samples(
        self, sd_lora, engine, run_id: str, step: int | None, prompt: str
    ) -> list[str]:
        """Generate the milestone (or final) sample set and upload to B2."""
        keys: list[str] = []
        images = sd_lora.generate_samples(
            engine, prompt, settings.local_samples_per_milestone, seed=step or 0
        )
        for index, png in enumerate(images):
            key = sample_key(run_id, step, index)
            put_object_bytes(key, png, "image/png")
            keys.append(key)
        return keys

    @staticmethod
    def _milestones(total_steps: int) -> set[int]:
        n = max(1, settings.local_milestones)
        return {max(1, round(total_steps * (m + 1) / n)) for m in range(n)}
