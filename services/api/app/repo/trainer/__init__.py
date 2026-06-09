"""Trainer adapter selection.

`get_trainer()` returns the adapter named by `settings.trainer_provider`.
Default is the simulated trainer (no GPU, no keys). "local" is a real on-device
SD 1.5 LoRA trainer (diffusers + peft); "replicate" is a not-wired stub. Both
optional adapters are imported lazily so their heavy deps stay off the default
path.
"""

from app.config import settings
from app.repo.trainer.base import (
    ProgressCallback,
    Trainer,
    TrainerResult,
    TrainerStep,
)
from app.repo.trainer.simulated import SimulatedTrainer


def get_trainer() -> Trainer:
    provider = (settings.trainer_provider or "simulated").lower()
    if provider == "replicate":
        # Imported here (not at module top) so the optional adapter — and any
        # SDK it lazily pulls in — is only touched when explicitly selected.
        from app.repo.trainer.replicate import ReplicateTrainer

        return ReplicateTrainer()
    if provider == "local":
        # Real on-device SD 1.5 LoRA trainer. Imported here so the heavy ML
        # stack (torch/diffusers/peft) is only touched when explicitly selected.
        from app.repo.trainer.local import LocalTrainer

        return LocalTrainer()
    return SimulatedTrainer()


__all__ = [
    "ProgressCallback",
    "Trainer",
    "TrainerResult",
    "TrainerStep",
    "get_trainer",
]
