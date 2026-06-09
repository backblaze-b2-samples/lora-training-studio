"""Default, offline captioner.

`TemplatedCaptioner` composes a caption from the run's instance token and the
image filename — no network, no API key, deterministic. It's the fallback
that makes "auto-caption all" work out of the box.
"""

import re
from pathlib import Path

_WORD_SPLIT_RE = re.compile(r"[_\-\s]+")


def _humanize_filename(filename: str) -> str:
    stem = Path(filename).stem
    # Drop trailing counters like "img_001" -> "img".
    stem = re.sub(r"\d+$", "", stem)
    words = [w for w in _WORD_SPLIT_RE.split(stem) if w]
    return " ".join(words).strip().lower()


class TemplatedCaptioner:
    name = "templated"

    def caption(self, instance_token: str, filename: str, image_bytes: bytes) -> str:
        descriptor = _humanize_filename(filename)
        token = instance_token.strip() or "sks"
        if descriptor:
            return f"a photo of {token}, {descriptor}"
        return f"a photo of {token}"
