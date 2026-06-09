from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    b2_endpoint: str = ""
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Per-dataset-image cap. Training images are small; keep this tight so a
    # stray multi-GB upload can't wedge a run.
    max_dataset_image_size: int = 25 * 1024 * 1024  # 25MB

    # --- Training engine selection ---
    # Which Trainer adapter drives a run. "simulated" (the default) needs no
    # GPU and no API keys — it emits placeholder checkpoints, a stub
    # .safetensors LoRA, and Pillow-rendered sample images with a synthetic
    # loss curve, so the whole pipeline is exercised on a stock laptop.
    # "replicate" is an optional, not-wired extension stub (see
    # repo/trainer/replicate.py) behind REPLICATE_API_TOKEN. "local" is a real,
    # opt-in trainer that fine-tunes a Stable Diffusion 1.5 LoRA on-device with
    # diffusers + peft (see repo/trainer/local.py); it needs the optional ML
    # deps and a GPU/MPS backend, so it is never the default.
    trainer_provider: str = "simulated"
    replicate_api_token: str = ""

    # Synthetic-trainer pacing: seconds of wall-clock per simulated step.
    # Small so a demo run completes in a few seconds.
    simulated_step_seconds: float = 0.4

    # --- Local (real) trainer settings (only used when TRAINER_PROVIDER=local) ---
    # HuggingFace repo id of the SD 1.5 base. fp32 is forced on MPS (fp16 NaNs,
    # bf16 unsupported for training on Metal). First run downloads ~4 GB.
    local_sd_model_id: str = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    local_train_resolution: int = 512
    # Checkpoints + sample sets emitted across a run, mirroring the simulated
    # cadence so B2 object counts stay bounded regardless of step count.
    local_milestones: int = 4
    local_samples_per_milestone: int = 4

    # --- Captioner selection ---
    # "templated" (the default) generates captions offline from the run's
    # instance token + filename — no network, no keys. "claude" uses
    # Anthropic vision (see repo/captioner/claude.py) and only works when
    # ANTHROPIC_API_KEY is set.
    captioner_provider: str = "templated"
    anthropic_api_key: str = ""
    claude_caption_model: str = "claude-haiku-4-5"

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
