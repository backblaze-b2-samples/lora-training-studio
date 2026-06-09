"""Optional cloud-training adapter — EXTENSION STUB, NOT WIRED.

This is a deliberately incomplete adapter that shows where real GPU training
would plug in. It implements the `Trainer` interface so the factory in
`__init__.py` can return it when `settings.trainer_provider == "replicate"`,
but `train()` raises `NotImplementedError`: actually driving a Replicate
training job (uploading the dataset, polling the prediction, streaming
checkpoints back to B2) is out of scope for this sample.

The `replicate` SDK is imported lazily inside `train()` so importing this
module never requires the dependency or a `REPLICATE_API_TOKEN`. The default
trainer is `SimulatedTrainer`, which needs neither.
"""

from app.config import settings
from app.repo.trainer.base import ProgressCallback, TrainerResult


class ReplicateTrainer:
    name = "replicate"

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
        # Lazy import: the SDK is only needed on this opt-in path.
        import replicate  # noqa: F401  (extension point — not yet wired)

        if not settings.replicate_api_token:
            raise RuntimeError(
                "trainer_provider=replicate requires REPLICATE_API_TOKEN. "
                "The default trainer (simulated) needs no key."
            )
        raise NotImplementedError(
            "ReplicateTrainer is an extension stub. Wire dataset upload, "
            "prediction polling, and checkpoint/LoRA write-back to B2 here. "
            "Use the simulated trainer for the zero-config demo."
        )
