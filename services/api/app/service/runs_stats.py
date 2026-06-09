"""Storage-lifecycle dashboard aggregation.

Computes run counts and a B2 storage breakdown by artifact category from a
single prefix-scoped listing of `lora-training/`. This is the "heavy across
the lifecycle" story: dataset, captions, checkpoints, the final LoRA, and the
sample gallery are each tallied separately.
"""

from app.repo import list_objects, list_run_prefixes, read_manifest
from app.types import (
    RunsStats,
    RunStatus,
    StorageBreakdown,
    StorageBreakdownItem,
)
from app.types.formatting import humanize_bytes

# Maps the path segment after `lora-training/{run_id}/` to a display category.
_CATEGORY_ORDER = ["dataset", "captions", "checkpoints", "lora", "samples", "manifest"]


def _categorize(key: str) -> str:
    # key: lora-training/{run_id}/{segment}/...  or  .../run.json
    parts = key.split("/")
    if len(parts) < 3:
        return "manifest"
    segment = parts[2]
    if segment == "run.json":
        return "manifest"
    if segment in _CATEGORY_ORDER:
        return segment
    return "manifest"


def _storage_breakdown(objects: list[dict]) -> StorageBreakdown:
    sizes: dict[str, int] = {c: 0 for c in _CATEGORY_ORDER}
    counts: dict[str, int] = {c: 0 for c in _CATEGORY_ORDER}
    for obj in objects:
        category = _categorize(obj["key"])
        sizes[category] += obj["size_bytes"]
        counts[category] += 1

    items = [
        StorageBreakdownItem(
            category=category,
            object_count=counts[category],
            size_bytes=sizes[category],
            size_human=humanize_bytes(sizes[category]),
        )
        for category in _CATEGORY_ORDER
        if counts[category] > 0
    ]
    total = sum(sizes.values())
    return StorageBreakdown(
        items=items,
        total_size_bytes=total,
        total_size_human=humanize_bytes(total),
    )


def get_runs_stats() -> RunsStats:
    objects = list_objects("lora-training/")
    breakdown = _storage_breakdown(objects)

    completed = 0
    loras = 0
    training_images = 0
    for run_id in list_run_prefixes():
        manifest = read_manifest(run_id)
        if manifest is None:
            continue
        if manifest.get("status") == RunStatus.COMPLETE.value:
            completed += 1
        if manifest.get("lora_key"):
            loras += 1
        training_images += len(manifest.get("dataset", []))

    return RunsStats(
        total_runs=len(list_run_prefixes()),
        completed_runs=completed,
        loras_produced=loras,
        training_images=training_images,
        storage=breakdown,
    )
