"""Unit tests for the local (real) SD 1.5 LoRA trainer.

The real training path needs the heavy ML stack (torch/diffusers/peft) and a
multi-minute GPU/MPS run, so it is not exercised in CI. These tests cover the
adapter's pure logic and the factory wiring — which need no torch (the ML stack
is imported lazily inside `train()`). The full end-to-end run is verified
manually (see docs/features/trainer-providers.md).
"""

import app.config
from app.repo.trainer import get_trainer
from app.repo.trainer.local import LocalTrainer, _ids_from_dataset_key


def test_factory_returns_local_trainer(monkeypatch):
    monkeypatch.setattr(app.config.settings, "trainer_provider", "local")
    trainer = get_trainer()
    assert isinstance(trainer, LocalTrainer)
    assert trainer.name == "local"


def test_ids_from_dataset_key():
    key = "lora-training/abc123/dataset/img00.jpg"
    assert _ids_from_dataset_key(key) == ("abc123", "img00")


def test_ids_from_dataset_key_rejects_non_dataset_key():
    assert _ids_from_dataset_key("lora-training/abc123/run.json") is None


def test_milestones_bounded_and_in_range():
    # A 1000-step run emits exactly LOCAL_MILESTONES (default 4) checkpoints,
    # never one per step — keeps the B2 object count bounded.
    assert LocalTrainer._milestones(1000) == {250, 500, 750, 1000}
    assert all(1 <= m <= 10 for m in LocalTrainer._milestones(10))
    assert LocalTrainer._milestones(1) == {1}
