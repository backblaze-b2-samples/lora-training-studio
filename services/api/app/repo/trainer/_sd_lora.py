"""Stable Diffusion 1.5 LoRA training internals (diffusers + peft, MPS/fp32).

These helpers hold every heavy ML dependency (torch, diffusers, transformers,
peft, torchvision). The module is imported *only* by `LocalTrainer.train()`
when `TRAINER_PROVIDER=local`, so the default (simulated) path never loads
torch. fp32 is mandatory on Apple's Metal (MPS) backend: fp16 produces NaN
loss and bf16 is unsupported for training, so all modules load in float32.

Only the UNet attention projections get LoRA adapters; the VAE and text encoder
stay frozen — the standard DreamBooth-LoRA recipe, and the lightest on memory.
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass

import torch
import torch.nn.functional as F
from diffusers import DDPMScheduler, StableDiffusionPipeline
from diffusers.utils import convert_state_dict_to_diffusers
from peft import LoraConfig
from peft.utils import get_peft_model_state_dict
from PIL import Image
from torchvision import transforms

# LoRA targets: the four attention projection layers in the UNet.
_TARGET_MODULES = ["to_k", "to_q", "to_v", "to_out.0"]
_DTYPE = torch.float32


@dataclass
class TrainExample:
    """One preprocessed training pair: normalized pixels + tokenized caption."""

    pixel_values: torch.Tensor  # [3, H, W], normalized to [-1, 1]
    input_ids: torch.Tensor  # [seq_len]


@dataclass
class Engine:
    """Loaded SD pipeline + training scaffolding for one run."""

    pipe: StableDiffusionPipeline
    noise_scheduler: DDPMScheduler
    optimizer: torch.optim.Optimizer
    device: torch.device
    resolution: int

    @property
    def unet(self):
        return self.pipe.unet

    @property
    def vae(self):
        return self.pipe.vae

    @property
    def text_encoder(self):
        return self.pipe.text_encoder

    @property
    def tokenizer(self):
        return self.pipe.tokenizer


def _select_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_engine(
    model_id: str, rank: int, learning_rate: float, resolution: int
) -> Engine:
    """Load SD 1.5, freeze the base, attach a UNet LoRA, and build an optimizer."""
    device = _select_device()
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        safety_checker=None,
        requires_safety_checker=False,
        torch_dtype=_DTYPE,
    )
    pipe.set_progress_bar_config(disable=True)

    # A DDPM scheduler is used for the training objective; the pipeline keeps
    # its own (PNDM) scheduler for sampling.
    noise_scheduler = DDPMScheduler.from_config(pipe.scheduler.config)

    pipe.vae.requires_grad_(False)
    pipe.text_encoder.requires_grad_(False)
    pipe.unet.requires_grad_(False)

    pipe.unet.add_adapter(
        LoraConfig(
            r=rank,
            lora_alpha=rank,
            init_lora_weights="gaussian",
            target_modules=_TARGET_MODULES,
        )
    )
    pipe.to(device)

    lora_params = [p for p in pipe.unet.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(lora_params, lr=learning_rate)
    return Engine(
        pipe=pipe,
        noise_scheduler=noise_scheduler,
        optimizer=optimizer,
        device=device,
        resolution=resolution,
    )


def prepare_examples(
    engine: Engine, items: list[tuple[bytes, str]]
) -> list[TrainExample]:
    """Decode image bytes and tokenize captions into training tensors."""
    tfm = transforms.Compose(
        [
            transforms.Resize(
                engine.resolution,
                interpolation=transforms.InterpolationMode.BILINEAR,
            ),
            transforms.CenterCrop(engine.resolution),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),
        ]
    )
    examples: list[TrainExample] = []
    for image_bytes, caption in items:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        input_ids = engine.tokenizer(
            caption,
            padding="max_length",
            truncation=True,
            max_length=engine.tokenizer.model_max_length,
            return_tensors="pt",
        ).input_ids[0]
        examples.append(
            TrainExample(pixel_values=tfm(image), input_ids=input_ids)
        )
    return examples


def train_step(engine: Engine, example: TrainExample) -> float:
    """Run one optimization step and return the scalar loss."""
    engine.unet.train()
    device = engine.device

    pixel_values = example.pixel_values.unsqueeze(0).to(device, dtype=_DTYPE)
    with torch.no_grad():
        latents = engine.vae.encode(pixel_values).latent_dist.sample()
        latents = latents * engine.vae.config.scaling_factor
        encoder_hidden_states = engine.text_encoder(
            example.input_ids.unsqueeze(0).to(device)
        )[0]

    noise = torch.randn_like(latents)
    timesteps = torch.randint(
        0,
        engine.noise_scheduler.config.num_train_timesteps,
        (latents.shape[0],),
        device=device,
    ).long()
    noisy = engine.noise_scheduler.add_noise(latents, noise, timesteps)

    model_pred = engine.unet(
        noisy, timesteps, encoder_hidden_states, return_dict=False
    )[0]
    if engine.noise_scheduler.config.prediction_type == "v_prediction":
        target = engine.noise_scheduler.get_velocity(latents, noise, timesteps)
    else:
        target = noise

    loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")
    engine.optimizer.zero_grad()
    loss.backward()
    engine.optimizer.step()
    return float(loss.detach().to("cpu"))


def generate_samples(
    engine: Engine,
    prompt: str,
    count: int,
    steps: int = 25,
    guidance: float = 7.5,
    seed: int = 0,
) -> list[bytes]:
    """Generate `count` PNG samples with the in-progress LoRA. Returns bytes."""
    engine.unet.eval()
    out: list[bytes] = []
    # CPU generator: MPS RNG is not seedable across all torch versions.
    generator = torch.Generator(device="cpu").manual_seed(seed)
    with torch.no_grad():
        for _ in range(count):
            image = engine.pipe(
                prompt,
                num_inference_steps=steps,
                guidance_scale=guidance,
                height=engine.resolution,
                width=engine.resolution,
                generator=generator,
            ).images[0]
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            out.append(buf.getvalue())
    engine.unet.train()
    if engine.device.type == "mps":
        torch.mps.empty_cache()
    return out


def lora_checkpoint_bytes(engine: Engine) -> bytes:
    """Serialize the current LoRA adapter state as a `.bin` checkpoint blob."""
    buf = io.BytesIO()
    torch.save(get_peft_model_state_dict(engine.unet), buf)
    return buf.getvalue()


def lora_safetensors_bytes(engine: Engine) -> bytes:
    """Export the trained LoRA as diffusers-format `.safetensors` bytes."""
    state = convert_state_dict_to_diffusers(get_peft_model_state_dict(engine.unet))
    with tempfile.TemporaryDirectory() as tmp:
        StableDiffusionPipeline.save_lora_weights(
            save_directory=tmp,
            unet_lora_layers=state,
            safe_serialization=True,
        )
        with open(os.path.join(tmp, "pytorch_lora_weights.safetensors"), "rb") as f:
            return f.read()
