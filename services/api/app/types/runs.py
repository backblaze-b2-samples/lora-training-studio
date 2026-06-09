from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    """Lifecycle of a single LoRA training run.

    The happy path walks forward through these states; `failed` is terminal
    and can be entered from any active state.
    """

    CREATED = "created"
    CAPTIONING = "captioning"
    READY_TO_TRAIN = "ready_to_train"
    TRAINING = "training"
    SAMPLING = "sampling"
    COMPLETE = "complete"
    FAILED = "failed"


class StageName(StrEnum):
    DATASET = "dataset"
    CAPTIONS = "captions"
    TRAINING = "training"
    SAMPLES = "samples"
    DOWNLOAD = "download"


class StageStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"


class RunConfig(BaseModel):
    """User-supplied training configuration. `base_model` is a display label
    only: the local (default) trainer always fine-tunes SD 1.5
    (`settings.local_sd_model_id`) and the simulated trainer loads no real
    weights."""

    base_model: str = "sd-1.5"
    instance_token: str = Field(default="sks", max_length=120)
    steps: int = Field(default=1000, ge=10, le=10000)
    rank: int = Field(default=16, ge=1, le=256)
    learning_rate: float = Field(default=1e-4, gt=0, le=1.0)


class StageState(BaseModel):
    name: StageName
    status: StageStatus = StageStatus.PENDING


class DatasetImage(BaseModel):
    image_id: str
    key: str
    filename: str
    size_bytes: int
    size_human: str
    content_type: str
    width: int | None = None
    height: int | None = None


class Caption(BaseModel):
    image_id: str
    text: str
    key: str


class SampleImage(BaseModel):
    key: str
    step: int | None = None  # None => final sample
    index: int


class LossPoint(BaseModel):
    step: int
    loss: float


class TrainingProgress(BaseModel):
    status: RunStatus
    current_step: int = 0
    total_steps: int = 0
    loss_curve: list[LossPoint] = Field(default_factory=list)
    latest_checkpoint_key: str | None = None
    message: str | None = None


class StorageBreakdownItem(BaseModel):
    category: str  # dataset | captions | checkpoints | lora | samples | manifest
    object_count: int
    size_bytes: int
    size_human: str


class StorageBreakdown(BaseModel):
    items: list[StorageBreakdownItem] = Field(default_factory=list)
    total_size_bytes: int = 0
    total_size_human: str = "0 B"


class RunSummary(BaseModel):
    run_id: str
    name: str
    status: RunStatus
    config: RunConfig
    image_count: int = 0
    created_at: datetime
    updated_at: datetime
    lora_key: str | None = None


class RunDetail(BaseModel):
    run_id: str
    name: str
    status: RunStatus
    config: RunConfig
    stages: list[StageState] = Field(default_factory=list)
    dataset: list[DatasetImage] = Field(default_factory=list)
    captions: list[Caption] = Field(default_factory=list)
    progress: TrainingProgress
    samples: list[SampleImage] = Field(default_factory=list)
    lora_key: str | None = None
    created_at: datetime
    updated_at: datetime


class RunsStats(BaseModel):
    total_runs: int
    completed_runs: int
    loras_produced: int
    training_images: int
    storage: StorageBreakdown


class CreateRunRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    config: RunConfig = Field(default_factory=RunConfig)


class CaptionUpdate(BaseModel):
    text: str = Field(default="", max_length=2000)
