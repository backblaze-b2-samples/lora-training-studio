"""End-to-end tests for the LoRA run pipeline against an in-memory B2 fake.

Patches `b2_client.get_s3_client` with a dict-backed fake S3 client so the
whole lifecycle (create -> dataset -> caption -> train -> samples -> LoRA)
runs without touching the network. The fixture pins the simulated trainer and
templated captioner so the zero-dependency SimulatedTrainer and
TemplatedCaptioner are exercised — no GPU, no API keys, no network — regardless
of the configured defaults or a local .env.
"""

import io
from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError
from PIL import Image

from app.config import settings
from app.repo import b2_client
from app.service import captioning, runs, runs_stats, training
from app.types import CreateRunRequest, RunConfig, RunStatus


class _FakeS3:
    """Minimal in-memory stand-in for the boto3 S3 client surface we use."""

    def __init__(self):
        self.store: dict[str, bytes] = {}

    def head_bucket(self, **_):
        return {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.store[Key] = Body.read()
        return {}

    def get_object(self, Bucket, Key):
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {
            "ContentLength": len(self.store[Key]),
            "ContentType": "application/octet-stream",
            "LastModified": datetime.now(UTC),
        }

    def delete_object(self, Bucket, Key):
        self.store.pop(Key, None)
        return {}

    def list_objects_v2(self, Bucket, Prefix="", MaxKeys=1000, **_):
        contents = [
            {"Key": k, "Size": len(v), "LastModified": datetime.now(UTC)}
            for k, v in self.store.items()
            if k.startswith(Prefix)
        ]
        return {"Contents": contents, "IsTruncated": False}

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://example.test/{Params['Key']}"


@pytest.fixture
def fake_b2(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake)
    # Pin the zero-dependency providers so these end-to-end tests stay hermetic
    # (no GPU, no API keys, no network) regardless of the configured defaults or
    # a local .env: the default trainer is "local" (a real, multi-minute SD 1.5
    # run needing torch) and a .env may set CAPTIONER_PROVIDER=claude.
    monkeypatch.setattr(settings, "trainer_provider", "simulated")
    monkeypatch.setattr(settings, "captioner_provider", "templated")
    monkeypatch.setattr(settings, "simulated_step_seconds", 0.0)
    return fake


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (120, 80, 200)).save(buf, format="PNG")
    return buf.getvalue()


def test_create_and_get_run(fake_b2):
    detail = runs.create_run(CreateRunRequest(name="My LoRA", config=RunConfig()))
    assert detail.status == RunStatus.CREATED
    fetched = runs.get_run(detail.run_id)
    assert fetched.name == "My LoRA"
    assert fetched.run_id == detail.run_id


def test_add_dataset_image_advances_status(fake_b2):
    detail = runs.create_run(CreateRunRequest(name="r", config=RunConfig()))
    img = runs.add_dataset_image(detail.run_id, _png_bytes(), "corgi.png", "image/png")
    assert img.width == 32 and img.height == 32
    updated = runs.get_run(detail.run_id)
    assert updated.status == RunStatus.CAPTIONING
    assert len(updated.dataset) == 1


def test_auto_caption_and_full_training(fake_b2):
    detail = runs.create_run(
        CreateRunRequest(name="r", config=RunConfig(instance_token="sks", steps=100))
    )
    runs.add_dataset_image(detail.run_id, _png_bytes(), "corgi_dog.png", "image/png")

    captions = captioning.auto_caption_all(detail.run_id)
    assert len(captions) == 1
    assert captions[0].text.startswith("a photo of sks")

    result = training.start_training(detail.run_id)
    assert result["status"] == RunStatus.TRAINING.value

    # Run the background job synchronously.
    training.run_training_job(detail.run_id)

    done = runs.get_run(detail.run_id)
    assert done.status == RunStatus.COMPLETE
    assert done.lora_key and done.lora_key.endswith(".safetensors")
    assert len(done.samples) > 0
    assert len(done.progress.loss_curve) > 0
    # Loss should trend downward across the run.
    losses = [p.loss for p in done.progress.loss_curve]
    assert losses[0] >= losses[-1]


def test_train_requires_captions(fake_b2):
    detail = runs.create_run(CreateRunRequest(name="r", config=RunConfig()))
    runs.add_dataset_image(detail.run_id, _png_bytes(), "a.png", "image/png")
    with pytest.raises(runs.RunError):
        training.start_training(detail.run_id)


def test_delete_run_clears_prefix(fake_b2):
    detail = runs.create_run(CreateRunRequest(name="r", config=RunConfig()))
    runs.add_dataset_image(detail.run_id, _png_bytes(), "a.png", "image/png")
    deleted = runs.delete_run(detail.run_id)
    assert deleted >= 2  # manifest + image
    with pytest.raises(runs.RunNotFound):
        runs.get_run(detail.run_id)


def test_runs_stats_breakdown(fake_b2):
    detail = runs.create_run(CreateRunRequest(name="r", config=RunConfig(steps=100)))
    runs.add_dataset_image(detail.run_id, _png_bytes(), "a.png", "image/png")
    captioning.auto_caption_all(detail.run_id)
    training.start_training(detail.run_id)
    training.run_training_job(detail.run_id)

    stats = runs_stats.get_runs_stats()
    assert stats.total_runs == 1
    assert stats.completed_runs == 1
    assert stats.loras_produced == 1
    assert stats.training_images == 1
    categories = {item.category for item in stats.storage.items}
    assert {"dataset", "captions", "checkpoints", "lora", "samples"} <= categories


def test_asset_url_rejects_cross_run_key(fake_b2):
    detail = runs.create_run(CreateRunRequest(name="r", config=RunConfig()))
    with pytest.raises(runs.RunError):
        runs.get_asset_url(detail.run_id, "lora-training/other-run/lora/x.safetensors")


@pytest.mark.asyncio
async def test_runs_http_roundtrip(client, fake_b2):
    create = await client.post("/runs", json={"name": "http run", "config": {}})
    assert create.status_code == 201
    run_id = create.json()["run_id"]

    listed = await client.get("/runs")
    assert listed.status_code == 200
    assert any(r["run_id"] == run_id for r in listed.json())

    stats = await client.get("/runs/stats")
    assert stats.status_code == 200
