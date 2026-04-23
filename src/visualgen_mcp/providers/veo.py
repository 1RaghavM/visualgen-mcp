"""Async video generation via Veo 3.1 (submit, poll, download)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from visualgen_mcp.config import (
    DEFAULT_VIDEO_DURATION_SECONDS,
    resolve_video_model,
    validate_video_params,
)


def submit(
    *,
    client: Any,
    prompt: str,
    tier: str,
    aspect_ratio: str,
    resolution: str,
    negative_prompt: str | None = None,
    image_path: str | None = None,
    duration_seconds: int = DEFAULT_VIDEO_DURATION_SECONDS,
) -> dict[str, Any]:
    """Submit a Veo generation job and return the raw operation plus model ID.

    Raises ValueError for invalid parameters. Actual API errors surface as
    whatever the google-genai SDK raises; callers should catch broadly.
    """
    validate_video_params(tier, aspect_ratio, resolution)
    model_id = resolve_video_model(tier)

    from google.genai import types

    config_kwargs: dict[str, Any] = {
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "number_of_videos": 1,
        "duration_seconds": duration_seconds,
    }
    if negative_prompt:
        config_kwargs["negative_prompt"] = negative_prompt

    call_kwargs: dict[str, Any] = {
        "model": model_id,
        "prompt": prompt,
        "config": types.GenerateVideosConfig(**config_kwargs),
    }
    if image_path:
        call_kwargs["image"] = _load_image(image_path)

    operation = client.models.generate_videos(**call_kwargs)
    return {"operation": operation, "model_id": model_id}


def poll(*, client: Any, operation: Any) -> Any:
    """Return the refreshed operation state."""
    return client.operations.get(operation)


def download(
    *,
    client: Any,
    operation: Any,
    output_dir: Path,
    tier: str,
) -> str:
    """Download the completed video to `output_dir` and return the absolute path."""
    response = getattr(operation, "response", None)
    if response is None:
        raise RuntimeError("Operation completed without a response payload")
    videos = getattr(response, "generated_videos", None) or []
    if not videos:
        raise RuntimeError(
            "Operation completed but returned no videos. The prompt may have been "
            "filtered by Google's content policy."
        )
    generated = videos[0]
    video_obj = generated.video
    client.files.download(file=video_obj)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"veo-{tier}-{timestamp}.mp4"
    video_obj.save(str(path))
    return str(path)


def extract_error(operation: Any) -> str:
    """Best-effort conversion of a failed operation's error to a string."""
    err = getattr(operation, "error", None)
    if err is None:
        return "Veo operation failed with no error message"
    message = getattr(err, "message", None)
    if message:
        return str(message)
    return str(err)


def _load_image(image_path: str) -> Any:
    from google.genai import types

    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"image_path does not exist: {image_path}")
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime_type = "image/jpeg"
    elif suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"
    else:
        raise ValueError(
            f"Unsupported image extension {suffix!r}. Use .png, .jpg, .jpeg, or .webp."
        )
    return types.Image(image_bytes=path.read_bytes(), mime_type=mime_type)


def list_videos(output_dir: Path) -> list[dict[str, Any]]:
    """Return metadata for every MP4 in `output_dir`, newest first."""
    if not output_dir.exists():
        return []
    entries: list[dict[str, Any]] = []
    for child in output_dir.iterdir():
        if child.is_file() and child.suffix.lower() == ".mp4":
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
