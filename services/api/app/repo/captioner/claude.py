"""Optional Claude-vision captioner.

`ClaudeCaptioner` sends each dataset image to the Anthropic Messages API and
asks for a concise training caption. It is OPTIONAL: it only runs when
`settings.captioner_provider == "claude"` AND `ANTHROPIC_API_KEY` is set. The
`anthropic` SDK is imported lazily inside `caption()` so importing this module
never requires the dependency. The offline `TemplatedCaptioner` is the default.
"""

import base64

from app.config import settings

_PROMPT = (
    "Write a single concise training caption for this image, suitable for "
    "LoRA fine-tuning. Begin with the instance token '{token}', then describe "
    "the subject and notable attributes in a comma-separated phrase. Reply "
    "with the caption only — no preamble, no quotes."
)

_MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return _MEDIA_TYPES.get(ext, "image/png")


class ClaudeCaptioner:
    name = "claude"

    def caption(self, instance_token: str, filename: str, image_bytes: bytes) -> str:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "captioner_provider=claude requires ANTHROPIC_API_KEY. "
                "The default captioner (templated) needs no key."
            )
        # Lazy import: only pulled in on this opt-in path.
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        encoded = base64.standard_b64encode(image_bytes).decode("ascii")
        message = client.messages.create(
            model=settings.claude_caption_model,
            max_tokens=120,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": _media_type(filename),
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": _PROMPT.format(token=instance_token.strip() or "sks"),
                        },
                    ],
                }
            ],
        )
        parts = [block.text for block in message.content if block.type == "text"]
        return " ".join(parts).strip()
