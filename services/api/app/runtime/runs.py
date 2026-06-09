"""Run pipeline routes: create/list/get/delete runs, manage the dataset,
caption images, launch training, and presign per-run assets.

No business logic here — every handler delegates to the service layer.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app.service import captioning, training
from app.service.runs import (
    RunError,
    add_dataset_image,
    create_run,
    delete_run,
    get_asset_url,
    get_run,
    list_runs,
    remove_dataset_image,
)
from app.service.runs_stats import get_runs_stats
from app.types import (
    Caption,
    CaptionUpdate,
    CreateRunRequest,
    DatasetImage,
    RunDetail,
    RunsStats,
    RunSummary,
    TrainingProgress,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle(exc: RunError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/runs", response_model=list[RunSummary])
async def list_runs_endpoint():
    return list_runs()


@router.get("/runs/stats", response_model=RunsStats)
async def runs_stats_endpoint():
    return get_runs_stats()


@router.post("/runs", response_model=RunDetail, status_code=201)
async def create_run_endpoint(req: CreateRunRequest):
    return create_run(req)


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run_endpoint(run_id: str):
    try:
        return get_run(run_id)
    except RunError as e:
        raise _handle(e) from None


@router.delete("/runs/{run_id}")
async def delete_run_endpoint(run_id: str):
    try:
        deleted = delete_run(run_id)
    except RunError as e:
        raise _handle(e) from None
    return {"deleted": True, "run_id": run_id, "objects": deleted}


@router.post("/runs/{run_id}/dataset", response_model=DatasetImage)
async def add_dataset_endpoint(run_id: str, file: UploadFile):
    content_type = file.content_type or "application/octet-stream"
    data = await file.read()
    try:
        return add_dataset_image(run_id, data, file.filename or "image", content_type)
    except RunError as e:
        raise _handle(e) from None


@router.delete("/runs/{run_id}/dataset/{image_id}")
async def remove_dataset_endpoint(run_id: str, image_id: str):
    try:
        remove_dataset_image(run_id, image_id)
    except RunError as e:
        raise _handle(e) from None
    return {"deleted": True, "image_id": image_id}


@router.get("/runs/{run_id}/captions", response_model=list[Caption])
async def get_captions_endpoint(run_id: str):
    try:
        return captioning.get_captions(run_id)
    except RunError as e:
        raise _handle(e) from None


@router.put("/runs/{run_id}/captions/{image_id}", response_model=Caption)
async def set_caption_endpoint(run_id: str, image_id: str, body: CaptionUpdate):
    try:
        return captioning.set_caption(run_id, image_id, body.text)
    except RunError as e:
        raise _handle(e) from None


@router.post("/runs/{run_id}/auto-caption", response_model=list[Caption])
async def auto_caption_endpoint(run_id: str):
    try:
        return captioning.auto_caption_all(run_id)
    except RunError as e:
        raise _handle(e) from None


@router.post("/runs/{run_id}/train")
async def start_training_endpoint(run_id: str, background_tasks: BackgroundTasks):
    try:
        result = training.start_training(run_id)
    except RunError as e:
        raise _handle(e) from None
    background_tasks.add_task(training.run_training_job, run_id)
    return result


@router.get("/runs/{run_id}/progress", response_model=TrainingProgress)
async def run_progress_endpoint(run_id: str):
    try:
        return get_run(run_id).progress
    except RunError as e:
        raise _handle(e) from None


@router.get("/runs/{run_id}/asset")
async def run_asset_endpoint(run_id: str, key: str):
    try:
        url = get_asset_url(run_id, key)
    except RunError as e:
        raise _handle(e) from None
    return {"url": url}
