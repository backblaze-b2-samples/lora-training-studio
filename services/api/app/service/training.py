"""Training orchestration.

`start_training` validates a run is ready, flips it to `training`, and hands
the work to a `BackgroundTasks` job (same pattern as the sibling samples).
The background job drives the configured trainer; on each step it persists the
loss point, latest checkpoint, and sample keys into the manifest so the UI can
poll progress. On completion it records the final LoRA + sample set and flips
the run to `complete`.
"""

import logging

from app.repo import read_manifest
from app.repo.trainer import TrainerStep, get_trainer
from app.service.runs import RunError, load_manifest, save_manifest
from app.types import LossPoint, RunStatus, SampleImage

logger = logging.getLogger(__name__)


def start_training(run_id: str) -> dict:
    """Validate readiness and flip the run into `training`. Returns the run id
    + status for the caller to schedule the background job against."""
    manifest = load_manifest(run_id)
    if not manifest.get("dataset"):
        raise RunError("Add dataset images before training")
    if not manifest.get("captions"):
        raise RunError("Caption the dataset before training")
    if manifest["status"] == RunStatus.TRAINING.value:
        raise RunError("Run is already training", status_code=409)

    total_steps = manifest["config"]["steps"]
    manifest["status"] = RunStatus.TRAINING.value
    manifest["lora_key"] = None
    manifest["samples"] = []
    manifest["progress"] = {
        "status": RunStatus.TRAINING.value,
        "current_step": 0,
        "total_steps": total_steps,
        "loss_curve": [],
        "latest_checkpoint_key": None,
        "message": "Training started",
    }
    save_manifest(manifest)
    return {"run_id": run_id, "status": manifest["status"]}


def run_training_job(run_id: str) -> None:
    """Background entrypoint. Drives the trainer and persists progress.

    Re-reads the manifest on every tick so a concurrent delete is noticed and
    failures are recorded into the manifest rather than crashing silently.
    """
    config = read_manifest(run_id)
    if config is None:
        return
    cfg = config["config"]
    dataset_keys = [img["key"] for img in config.get("dataset", [])]

    def on_progress(step: TrainerStep) -> None:
        manifest = read_manifest(run_id)
        if manifest is None:  # run deleted mid-flight
            return
        progress = manifest.setdefault("progress", {})
        progress["status"] = RunStatus.TRAINING.value
        progress["current_step"] = step.step
        progress["total_steps"] = step.total_steps
        progress.setdefault("loss_curve", []).append(
            LossPoint(step=step.step, loss=step.loss).model_dump()
        )
        progress["latest_checkpoint_key"] = step.checkpoint_key
        progress["message"] = step.message
        for index, key in enumerate(step.sample_keys):
            manifest.setdefault("samples", []).append(
                SampleImage(key=key, step=step.step, index=index).model_dump()
            )
        save_manifest(manifest)

    trainer = get_trainer()
    try:
        result = trainer.train(
            run_id=run_id,
            instance_token=cfg["instance_token"],
            total_steps=cfg["steps"],
            rank=cfg["rank"],
            learning_rate=cfg["learning_rate"],
            dataset_keys=dataset_keys,
            on_progress=on_progress,
        )
    except Exception as exc:  # record failure into the manifest, never crash
        logger.error("Training failed for run_id=%s: %s", run_id, exc, exc_info=True)
        manifest = read_manifest(run_id)
        if manifest is not None:
            manifest["status"] = RunStatus.FAILED.value
            manifest.setdefault("progress", {})["status"] = RunStatus.FAILED.value
            manifest["progress"]["message"] = f"Training failed: {exc}"
            save_manifest(manifest)
        return

    manifest = read_manifest(run_id)
    if manifest is None:
        return
    manifest["status"] = RunStatus.SAMPLING.value
    for index, key in enumerate(result.final_sample_keys):
        manifest.setdefault("samples", []).append(
            SampleImage(key=key, step=None, index=index).model_dump()
        )
    manifest["lora_key"] = result.lora_key
    manifest["status"] = RunStatus.COMPLETE.value
    manifest.setdefault("progress", {})["status"] = RunStatus.COMPLETE.value
    manifest["progress"]["message"] = "Training complete"
    save_manifest(manifest)
    logger.info("Training complete for run_id=%s lora=%s", run_id, result.lora_key)
