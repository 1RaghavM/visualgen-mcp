"""Synchronous image generation via Imagen 4 and Gemini 2.5 Flash Image."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from visualgen_mcp.config import resolve_image_model, validate_image_params


def generate_image(
    *,
    client: Any,
    prompt: str,
    model_alias: str,
    aspect_ratio: str,
    output_dir: Path,
    negative_prompt: str | None = None,
) -> dict[str, str]:
    """Generate an image and write it to `output_dir`.

    Returns a dict with the absolute `path` to the PNG file and the
    `model_used` (the resolved model ID, not the alias).
    """
    validate_image_params(aspect_ratio)
    model_id = resolve_image_model(model_alias)

    if model_alias == "nano-banana":
        image_bytes = _generate_nano_banana(client, model_id, prompt, aspect_ratio)
    elif model_alias == "imagen":
        image_bytes = _generate_imagen(client, model_id, prompt, aspect_ratio, negative_prompt)
    else:
        raise ValueError(f"No generator wired for model alias {model_alias!r}")

    path = output_dir / _make_filename(model_alias)
    path.write_bytes(image_bytes)
    return {"path": str(path), "model_used": model_id}


def _generate_nano_banana(client: Any, model_id: str, prompt: str, aspect_ratio: str) -> bytes:
    from google.genai import types

    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
        ),
    )
    for candidate in response.candidates:
        for part in candidate.content.parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None and inline.data:
                return bytes(inline.data)
    raise RuntimeError(
        "Nano Banana returned no image data. The prompt may have been filtered "
        "by Google's content policy, or the model produced only text."
    )


def _generate_imagen(
    client: Any,
    model_id: str,
    prompt: str,
    aspect_ratio: str,
    negative_prompt: str | None,
) -> bytes:
    from google.genai import types

    config_kwargs: dict[str, Any] = {
        "number_of_images": 1,
        "aspect_ratio": aspect_ratio,
    }
    if negative_prompt:
        config_kwargs["negative_prompt"] = negative_prompt

    response = client.models.generate_images(
        model=model_id,
        prompt=prompt,
        config=types.GenerateImagesConfig(**config_kwargs),
    )
    if not response.generated_images:
        raise RuntimeError(
            "Imagen returned no images. The prompt may have been filtered "
            "by Google's content policy."
        )
    return bytes(response.generated_images[0].image.image_bytes)


def _make_filename(alias: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{alias}-{timestamp}.png"


def list_images(output_dir: Path) -> list[dict[str, Any]]:
    """Return metadata for every PNG in `output_dir`, newest first."""
    if not output_dir.exists():
        return []
    entries: list[dict[str, Any]] = []
    for child in output_dir.iterdir():
        if child.is_file() and child.suffix.lower() == ".png":
            stat = child.stat()
            entries.append(
                {
                    "path": str(child.resolve()),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                }
            )
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return entries
