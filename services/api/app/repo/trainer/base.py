"""Trainer adapter protocol.

A `Trainer` drives one run: it emits step-by-step progress, writes
intermediate checkpoints and a growing sample gallery to B2, and produces
the final `.safetensors` LoRA. Implementations live alongside this file and
are selected in `config` (`settings.trainer_provider`). External training
SDKs (e.g. `replicate`) are imported *lazily inside their adapter* so the
default path needs no GPU and no API keys.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class TrainerStep:
    """One progress tick emitted by a trainer."""

    step: int
    total_steps: int
    loss: float
    checkpoint_key: str | None = None
    sample_keys: list[str] = field(default_factory=list)
    message: str | None = None


@dataclass
class TrainerResult:
    """Terminal output of a completed run."""

    lora_key: str
    final_sample_keys: list[str] = field(default_factory=list)


# A trainer reports progress by invoking this callback after each step. The
# service persists the tick into the run manifest.
ProgressCallback = Callable[[TrainerStep], None]


class Trainer(Protocol):
    """Drive a training run, persisting artifacts to B2 as it goes."""

    name: str

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
        """Run training to completion, calling `on_progress` per step and
        writing checkpoints / samples / the final LoRA to B2. Returns the
        final artifact keys. Raises on unrecoverable failure."""
        ...
