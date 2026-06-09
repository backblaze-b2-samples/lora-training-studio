"""Captioner adapter protocol.

A `Captioner` turns a dataset image into a training caption. Implementations
are selected in `config` (`settings.captioner_provider`). The default
(`TemplatedCaptioner`) is fully offline; the Claude adapter imports the
`anthropic` SDK lazily and only works when `ANTHROPIC_API_KEY` is set.
"""

from typing import Protocol


class Captioner(Protocol):
    name: str

    def caption(self, instance_token: str, filename: str, image_bytes: bytes) -> str:
        """Return a caption string for a single image."""
        ...
