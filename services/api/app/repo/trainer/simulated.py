"""Default, zero-dependency trainer.

`SimulatedTrainer` exercises the entire pipeline on a stock laptop with no
GPU and no API keys. It does NOT train anything real — it emits a synthetic
decreasing loss curve over time, writes placeholder checkpoint blobs and a
stub `.safetensors` LoRA, and renders sample-gallery PNGs with Pillow so the
B2 storage lifecycle (dataset -> captions -> checkpoints -> LoRA -> samples)
is fully populated and addressable.
"""

import hashlib
import io
import math
import time

from app.config import settings
from app.repo.b2_client import put_object_bytes
from app.repo.runs_store import checkpoint_key, lora_key, sample_key
from app.repo.trainer.base import ProgressCallback, TrainerResult, TrainerStep

# How many checkpoints + sample sets to emit across a run, regardless of the
# configured step count. Keeps a 1000-step demo from writing 1000 objects.
_MILESTONES = 4
_SAMPLES_PER_MILESTONE = 4
_SAMPLE_SIZE = 320


def _synthetic_loss(step: int, total: int) -> float:
    """Smooth exponential decay from ~0.42 toward ~0.04, plus a deterministic
    wobble so the curve looks like a real training run rather than a line."""
    progress = step / max(total, 1)
    base = 0.04 + 0.38 * math.exp(-3.2 * progress)
    wobble = 0.012 * math.sin(step * 0.7)
    return round(max(base + wobble, 0.01), 4)


def _render_sample(run_id: str, step: int | None, index: int) -> bytes:
    """Render a deterministic placeholder PNG. Color is seeded from the run +
    step + index so the gallery looks varied but is reproducible."""
    from PIL import Image, ImageDraw

    seed = f"{run_id}:{step}:{index}".encode()
    digest = hashlib.sha256(seed).digest()
    bg = (digest[0], digest[1], digest[2])
    fg = (255 - digest[0], 255 - digest[1], 255 - digest[2])

    img = Image.new("RGB", (_SAMPLE_SIZE, _SAMPLE_SIZE), bg)
    draw = ImageDraw.Draw(img)
    # A few concentric frames keyed off the digest — purely decorative.
    for i in range(4):
        inset = 24 + i * 28 + (digest[3 + i] % 12)
        draw.rectangle(
            [inset, inset, _SAMPLE_SIZE - inset, _SAMPLE_SIZE - inset],
            outline=fg,
            width=3,
        )
    label = "final" if step is None else f"step {step}"
    draw.text((16, 16), f"{label} · #{index}", fill=fg)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class SimulatedTrainer:
    name = "simulated"

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
        milestone_steps = [
            max(1, round(total_steps * (m + 1) / _MILESTONES))
            for m in range(_MILESTONES)
        ]

        for step in milestone_steps:
            # Simulate wall-clock work so the UI's loss curve fills in live.
            time.sleep(max(settings.simulated_step_seconds, 0.0))

            ckpt_key = checkpoint_key(run_id, step)
            # Placeholder checkpoint: a small deterministic blob, not weights.
            blob = hashlib.sha256(f"{run_id}:ckpt:{step}".encode()).digest() * 8
            put_object_bytes(ckpt_key, blob, "application/octet-stream")

            sample_keys: list[str] = []
            for index in range(_SAMPLES_PER_MILESTONE):
                key = sample_key(run_id, step, index)
                put_object_bytes(key, _render_sample(run_id, step, index), "image/png")
                sample_keys.append(key)

            on_progress(
                TrainerStep(
                    step=step,
                    total_steps=total_steps,
                    loss=_synthetic_loss(step, total_steps),
                    checkpoint_key=ckpt_key,
                    sample_keys=sample_keys,
                    message=f"Checkpoint at step {step}",
                )
            )

        # Final sample set + stub LoRA.
        final_samples: list[str] = []
        for index in range(_SAMPLES_PER_MILESTONE):
            key = sample_key(run_id, None, index)
            put_object_bytes(key, _render_sample(run_id, None, index), "image/png")
            final_samples.append(key)

        final_lora_key = lora_key(run_id)
        # Stub .safetensors: a tiny header-like blob keyed off the run config.
        seed = f"{run_id}:{instance_token}:{rank}:{learning_rate}".encode()
        lora_blob = b"SIMULATED_LORA\x00" + hashlib.sha256(seed).digest() * 32
        put_object_bytes(final_lora_key, lora_blob, "application/octet-stream")

        return TrainerResult(lora_key=final_lora_key, final_sample_keys=final_samples)
