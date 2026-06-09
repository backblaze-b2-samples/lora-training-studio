"""Captioner adapter selection.

`get_captioner()` returns the adapter named by `settings.captioner_provider`.
Default is the offline templated captioner. The Claude adapter is optional and
requires `ANTHROPIC_API_KEY`.
"""

from app.config import settings
from app.repo.captioner.base import Captioner
from app.repo.captioner.templated import TemplatedCaptioner


def get_captioner() -> Captioner:
    provider = (settings.captioner_provider or "templated").lower()
    if provider == "claude":
        # Imported here so the optional adapter and its lazy SDK are only
        # touched when explicitly selected.
        from app.repo.captioner.claude import ClaudeCaptioner

        return ClaudeCaptioner()
    return TemplatedCaptioner()


__all__ = ["Captioner", "get_captioner"]
