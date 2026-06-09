"""Captioning: per-image manual edits and one-click auto-caption.

Captions are stored both in the run manifest (for fast reads) and as
`lora-training/{run_id}/captions/{image_id}.txt` objects on B2 (versioned
alongside the dataset). Auto-caption drives the configured captioner adapter
(offline templated by default, Claude vision when enabled).
"""

import logging

from app.repo import get_object_bytes, put_object_bytes
from app.repo.captioner import get_captioner
from app.service.runs import RunError, load_manifest, save_manifest
from app.types import Caption, RunStatus

logger = logging.getLogger(__name__)


def _caption_key(run_id: str, image_id: str) -> str:
    return f"lora-training/{run_id}/captions/{image_id}.txt"


def _image_in_dataset(manifest: dict, image_id: str) -> dict | None:
    for img in manifest.get("dataset", []):
        if img["image_id"] == image_id:
            return img
    return None


def _upsert_caption(manifest: dict, run_id: str, image_id: str, text: str) -> Caption:
    key = _caption_key(run_id, image_id)
    put_object_bytes(key, text.encode("utf-8"), "text/plain")
    caption = Caption(image_id=image_id, text=text, key=key)
    captions = [c for c in manifest.get("captions", []) if c["image_id"] != image_id]
    captions.append(caption.model_dump())
    manifest["captions"] = captions
    return caption


def get_captions(run_id: str) -> list[Caption]:
    manifest = load_manifest(run_id)
    return [Caption(**c) for c in manifest.get("captions", [])]


def set_caption(run_id: str, image_id: str, text: str) -> Caption:
    manifest = load_manifest(run_id)
    if _image_in_dataset(manifest, image_id) is None:
        raise RunError("Image not found in dataset", status_code=404)
    caption = _upsert_caption(manifest, run_id, image_id, text.strip())
    save_manifest(manifest)
    return caption


def auto_caption_all(run_id: str) -> list[Caption]:
    """Generate a caption for every dataset image via the configured adapter.

    Reads each image's bytes back from B2 and feeds them to the captioner.
    The offline templated captioner ignores the bytes; the Claude adapter
    sends them to the vision model.
    """
    manifest = load_manifest(run_id)
    dataset = manifest.get("dataset", [])
    if not dataset:
        raise RunError("Add dataset images before captioning")

    captioner = get_captioner()
    instance_token = manifest["config"]["instance_token"]
    results: list[Caption] = []
    for img in dataset:
        image_bytes = get_object_bytes(img["key"]) or b""
        text = captioner.caption(instance_token, img["filename"], image_bytes)
        results.append(_upsert_caption(manifest, run_id, img["image_id"], text.strip()))

    if manifest["status"] in (RunStatus.CREATED.value, RunStatus.CAPTIONING.value):
        manifest["status"] = RunStatus.READY_TO_TRAIN.value
        manifest["progress"]["status"] = RunStatus.READY_TO_TRAIN.value
    save_manifest(manifest)
    logger.info(
        "Auto-captioned run_id=%s images=%d provider=%s",
        run_id,
        len(results),
        captioner.name,
    )
    return results
