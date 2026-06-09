"""Run-manifest persistence on B2.

Every run owns one prefix — `lora-training/{run_id}/` — and a `run.json`
manifest at its root. This module is the *only* place that knows the prefix
layout and the manifest object key; services and routers address runs by
`run_id` and never compose S3 keys themselves.

The manifest is stored as raw JSON (a plain dict). The service layer owns the
mapping to/from typed Pydantic models, so this stays a thin data-access shim.
"""

import json

from app.repo.b2_client import (
    delete_prefix,
    get_object_bytes,
    list_objects,
    put_object_bytes,
)

RUN_PREFIX = "lora-training/"
MANIFEST_NAME = "run.json"


def run_prefix(run_id: str) -> str:
    return f"{RUN_PREFIX}{run_id}/"


def manifest_key(run_id: str) -> str:
    return f"{run_prefix(run_id)}{MANIFEST_NAME}"


def checkpoint_key(run_id: str, step: int) -> str:
    """Intermediate checkpoint object key for a given training step."""
    return f"{run_prefix(run_id)}checkpoints/step-{step:06d}.bin"


def sample_key(run_id: str, step: int | None, index: int) -> str:
    """Sample-gallery image key. `step=None` is the final sample set."""
    folder = "final" if step is None else f"step-{step:06d}"
    return f"{run_prefix(run_id)}samples/{folder}/sample-{index:02d}.png"


def lora_key(run_id: str) -> str:
    """Final downloadable `.safetensors` LoRA key for a run."""
    return f"{run_prefix(run_id)}lora/{run_id}.safetensors"


def caption_key(run_id: str, image_id: str) -> str:
    """Caption text key for a dataset image."""
    return f"{run_prefix(run_id)}captions/{image_id}.txt"


def write_manifest(run_id: str, manifest: dict) -> None:
    """Persist a run manifest as `lora-training/{run_id}/run.json`."""
    body = json.dumps(manifest, default=str).encode("utf-8")
    put_object_bytes(manifest_key(run_id), body, "application/json")


def read_manifest(run_id: str) -> dict | None:
    """Read and parse a run manifest. Returns None if the run does not exist."""
    raw = get_object_bytes(manifest_key(run_id))
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def list_run_prefixes() -> list[str]:
    """Return the distinct run_ids that have objects under the run prefix.

    Derived from a single prefix-scoped list — no per-run round trips.
    """
    run_ids: list[str] = []
    seen: set[str] = set()
    for obj in list_objects(RUN_PREFIX):
        # key shape: lora-training/{run_id}/...
        remainder = obj["key"][len(RUN_PREFIX):]
        run_id = remainder.split("/", 1)[0]
        if run_id and run_id not in seen:
            seen.add(run_id)
            run_ids.append(run_id)
    return run_ids


def delete_run_prefix(run_id: str) -> int:
    """Delete every object under a run's prefix. Returns the count deleted."""
    return delete_prefix(run_prefix(run_id))
