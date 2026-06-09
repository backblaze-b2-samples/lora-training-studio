"""Run lifecycle: create, read, list, delete, and dataset management.

Owns the manifest shape (a plain dict persisted by `repo.runs_store`) and the
mapping to/from typed Pydantic models. Routers and other services address runs
by `run_id` and go through this module — they never touch the manifest dict or
compose S3 keys directly.
"""

import logging
import re
import uuid
from datetime import UTC, datetime

from app.repo import (
    delete_run_prefix,
    get_file_metadata,
    list_run_prefixes,
    put_object_bytes,
    read_manifest,
    write_manifest,
)
from app.service.metadata import extract_metadata
from app.types import (
    CreateRunRequest,
    DatasetImage,
    RunConfig,
    RunDetail,
    RunStatus,
    RunSummary,
    StageName,
    StageState,
    StageStatus,
    TrainingProgress,
)

logger = logging.getLogger(__name__)

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXT_FOR_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
_RUN_ID_RE = re.compile(r"^[a-z0-9-]{8,40}$")


class RunError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class RunNotFound(RunError):
    def __init__(self, run_id: str):
        super().__init__(f"Run '{run_id}' not found", status_code=404)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_manifest(run_id: str, name: str, config: RunConfig) -> dict:
    ts = _now()
    return {
        "run_id": run_id,
        "name": name,
        "status": RunStatus.CREATED.value,
        "config": config.model_dump(),
        "dataset": [],
        "captions": [],
        "samples": [],
        "progress": TrainingProgress(status=RunStatus.CREATED).model_dump(),
        "lora_key": None,
        "created_at": ts,
        "updated_at": ts,
    }


def _stages_for(manifest: dict) -> list[StageState]:
    """Derive the stepper state from the manifest, purely from data already
    present — no extra storage."""
    status = manifest["status"]
    has_dataset = len(manifest.get("dataset", [])) > 0
    has_captions = len(manifest.get("captions", [])) > 0
    has_lora = manifest.get("lora_key") is not None

    def st(done: bool, active: bool) -> StageStatus:
        if done:
            return StageStatus.DONE
        return StageStatus.ACTIVE if active else StageStatus.PENDING

    training_done = status in (RunStatus.SAMPLING.value, RunStatus.COMPLETE.value)
    return [
        StageState(name=StageName.DATASET, status=st(has_dataset, not has_dataset)),
        StageState(name=StageName.CAPTIONS, status=st(has_captions, has_dataset and not has_captions)),
        StageState(name=StageName.TRAINING, status=st(training_done, status == RunStatus.TRAINING.value)),
        StageState(name=StageName.SAMPLES, status=st(has_lora, status == RunStatus.SAMPLING.value)),
        StageState(name=StageName.DOWNLOAD, status=st(has_lora, False)),
    ]


def _to_detail(manifest: dict) -> RunDetail:
    return RunDetail(
        run_id=manifest["run_id"],
        name=manifest["name"],
        status=manifest["status"],
        config=manifest["config"],
        stages=_stages_for(manifest),
        dataset=manifest.get("dataset", []),
        captions=manifest.get("captions", []),
        progress=manifest.get("progress", {"status": manifest["status"]}),
        samples=manifest.get("samples", []),
        lora_key=manifest.get("lora_key"),
        created_at=manifest["created_at"],
        updated_at=manifest["updated_at"],
    )


def _to_summary(manifest: dict) -> RunSummary:
    return RunSummary(
        run_id=manifest["run_id"],
        name=manifest["name"],
        status=manifest["status"],
        config=manifest["config"],
        image_count=len(manifest.get("dataset", [])),
        created_at=manifest["created_at"],
        updated_at=manifest["updated_at"],
        lora_key=manifest.get("lora_key"),
    )


def load_manifest(run_id: str) -> dict:
    if not _RUN_ID_RE.match(run_id):
        raise RunError("Invalid run id")
    manifest = read_manifest(run_id)
    if manifest is None:
        raise RunNotFound(run_id)
    return manifest


def save_manifest(manifest: dict) -> None:
    manifest["updated_at"] = _now()
    write_manifest(manifest["run_id"], manifest)


def create_run(req: CreateRunRequest) -> RunDetail:
    run_id = uuid.uuid4().hex[:12]
    manifest = _new_manifest(run_id, req.name.strip(), req.config)
    write_manifest(run_id, manifest)
    logger.info("Run created: run_id=%s name=%s", run_id, req.name)
    return _to_detail(manifest)


def get_run(run_id: str) -> RunDetail:
    return _to_detail(load_manifest(run_id))


def list_runs() -> list[RunSummary]:
    summaries: list[RunSummary] = []
    for run_id in list_run_prefixes():
        manifest = read_manifest(run_id)
        if manifest is not None:
            summaries.append(_to_summary(manifest))
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def delete_run(run_id: str) -> int:
    if not _RUN_ID_RE.match(run_id):
        raise RunError("Invalid run id")
    deleted = delete_run_prefix(run_id)
    if deleted == 0:
        raise RunNotFound(run_id)
    logger.info("Run deleted: run_id=%s objects=%d", run_id, deleted)
    return deleted


def add_dataset_image(
    run_id: str, file_data: bytes, filename: str, content_type: str
) -> DatasetImage:
    manifest = load_manifest(run_id)
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise RunError(f"Image type '{content_type}' not allowed", status_code=415)
    if len(file_data) == 0:
        raise RunError("Empty file")

    image_id = uuid.uuid4().hex[:12]
    ext = _EXT_FOR_TYPE[content_type]
    key = f"lora-training/{run_id}/dataset/{image_id}.{ext}"
    put_object_bytes(key, file_data, content_type)

    meta = extract_metadata(file_data, filename, content_type)
    image = DatasetImage(
        image_id=image_id,
        key=key,
        filename=filename,
        size_bytes=meta.size_bytes,
        size_human=meta.size_human,
        content_type=content_type,
        width=meta.image_width,
        height=meta.image_height,
    )
    manifest["dataset"].append(image.model_dump())
    if manifest["status"] == RunStatus.CREATED.value:
        manifest["status"] = RunStatus.CAPTIONING.value
        manifest["progress"]["status"] = RunStatus.CAPTIONING.value
    save_manifest(manifest)
    return image


def remove_dataset_image(run_id: str, image_id: str) -> None:
    from app.repo import delete_file

    manifest = load_manifest(run_id)
    remaining = []
    removed = None
    for img in manifest["dataset"]:
        if img["image_id"] == image_id:
            removed = img
        else:
            remaining.append(img)
    if removed is None:
        raise RunError("Image not found", status_code=404)
    delete_file(removed["key"])
    # Drop any caption tied to the removed image.
    manifest["captions"] = [
        c for c in manifest.get("captions", []) if c["image_id"] != image_id
    ]
    manifest["dataset"] = remaining
    save_manifest(manifest)


def get_asset_url(run_id: str, key: str) -> str:
    """Presign a per-run asset for inline/thumbnail viewing or LoRA download.

    The key must belong to the run's prefix (defends against cross-run access).
    """
    from app.repo import get_presigned_url

    load_manifest(run_id)  # validates run id + existence
    prefix = f"lora-training/{run_id}/"
    if not key.startswith(prefix):
        raise RunError("Asset does not belong to this run")
    is_lora = key.endswith(".safetensors")
    meta = get_file_metadata(key)
    if meta is None:
        raise RunError("Asset not found", status_code=404)
    return get_presigned_url(key, filename=meta.filename, inline=not is_lora)
