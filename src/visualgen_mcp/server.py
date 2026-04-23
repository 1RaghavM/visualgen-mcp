"""FastMCP server wiring the six visual-generation tools to providers."""

from __future__ import annotations

import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from visualgen_mcp.config import (
    DEFAULT_VIDEO_DURATION_SECONDS,
    VIDEO_MODELS,
    Config,
)
from visualgen_mcp.jobs import JobStatus, JobStore
from visualgen_mcp.providers import imagen, veo

mcp = FastMCP("visualgen-mcp")

_job_store = JobStore()
_config: Config | None = None
_client: Any | None = None


def _get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def _get_client() -> Any:
    """Lazily build the google-genai client from the resolved API key."""
    global _client
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=_get_config().api_key)
    return _client


def _tier_from_model_id(model_id: str) -> str:
    """Reverse-lookup the tier alias from the resolved model ID."""
    for alias, mid in VIDEO_MODELS.items():
        if mid == model_id:
            return alias
    return "fast"


def _estimated_seconds(tier: str) -> int:
    return {"lite": 45, "fast": 60, "standard": 90}.get(tier, 60)


@mcp.tool()
def submit_video(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    resolution: str = "720p",
    negative_prompt: str | None = None,
    image_path: str | None = None,
) -> dict[str, Any]:
    """Submit a Veo 3.1 video generation job. Returns immediately with a job_id.

    Videos typically take 30-120 seconds. Call check_video(job_id) to poll
    for completion. The final MP4 is written to the configured OUTPUT_DIR
    and its absolute path is returned by check_video once ready.

    Args:
        prompt: Text description of the video to generate.
        model: "lite" (cheapest), "fast" (good balance), or "standard"
          (highest quality, most expensive). Defaults to your configured
          default video tier (run `visualgen-mcp init` to change).
        aspect_ratio: "16:9" (landscape) or "9:16" (portrait). Defaults to
          your configured default video aspect ratio.
        resolution: "720p", "1080p", or "4k". "4k" is rejected for model="lite".
        negative_prompt: Optional text describing what to avoid.
        image_path: Optional absolute path to a PNG/JPEG/WebP file to use as
          the starting frame for image-to-video generation.
    """
    cfg = _get_config()
    if model is None:
        model = cfg.default_video_tier
    if aspect_ratio is None:
        aspect_ratio = cfg.default_video_aspect_ratio
    client = _get_client()
    try:
        submission = veo.submit(
            client=client,
            prompt=prompt,
            tier=model,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            negative_prompt=negative_prompt,
            image_path=image_path,
        )
    except (ValueError, FileNotFoundError) as exc:
        return {"status": "error", "error": str(exc)}

    job = _job_store.create(
        model=submission["model_id"],
        operation=submission["operation"],
        requested_duration_seconds=DEFAULT_VIDEO_DURATION_SECONDS,
    )
    return {
        "job_id": job.job_id,
        "status": "submitted",
        "model": submission["model_id"],
        "estimated_seconds": _estimated_seconds(model),
    }


@mcp.tool()
def check_video(job_id: str) -> dict[str, Any]:
    """Check a video generation job. Downloads the file when ready.

    Returns one of three shapes:
      - {"status": "pending", "elapsed_seconds": int}
      - {"status": "complete", "path": str, "duration_seconds": float}
      - {"status": "failed", "error": str}

    Safe to call repeatedly. Once a job is complete or failed, subsequent
    calls return the cached terminal state without re-polling.

    Args:
        job_id: The id returned by submit_video.
    """
    job = _job_store.get(job_id)
    if job is None:
        return {"status": "failed", "error": f"Job {job_id!r} not found"}
    if job.status == JobStatus.COMPLETE:
        return {
            "status": "complete",
            "path": job.result_path,
            "duration_seconds": float(job.requested_duration_seconds),
        }
    if job.status == JobStatus.FAILED:
        return {"status": "failed", "error": job.error or "unknown error"}

    client = _get_client()
    try:
        fresh = veo.poll(client=client, operation=job.operation)
    except Exception as exc:  # noqa: BLE001 - SDK exceptions vary
        job.status = JobStatus.FAILED
        job.error = f"Polling failed: {exc}"
        _job_store.update(job)
        return {"status": "failed", "error": job.error}

    job.operation = fresh
    if not getattr(fresh, "done", False):
        _job_store.update(job)
        return {"status": "pending", "elapsed_seconds": job.elapsed_seconds}

    if getattr(fresh, "error", None) is not None:
        job.status = JobStatus.FAILED
        job.error = veo.extract_error(fresh)
        _job_store.update(job)
        return {"status": "failed", "error": job.error}

    try:
        path = veo.download(
            client=client,
            operation=fresh,
            output_dir=_get_config().output_dir,
            tier=_tier_from_model_id(job.model),
        )
    except Exception as exc:  # noqa: BLE001 - SDK exceptions vary
        job.status = JobStatus.FAILED
        job.error = f"Download failed: {exc}"
        _job_store.update(job)
        return {"status": "failed", "error": job.error}

    job.status = JobStatus.COMPLETE
    job.result_path = path
    _job_store.update(job)
    return {
        "status": "complete",
        "path": path,
        "duration_seconds": float(job.requested_duration_seconds),
    }


@mcp.tool()
def list_videos() -> list[dict[str, Any]]:
    """List every MP4 file in the configured OUTPUT_DIR, newest first.

    Each entry has absolute path, size in bytes, and creation timestamp.
    """
    return veo.list_videos(_get_config().output_dir)


@mcp.tool()
def generate_image(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    negative_prompt: str | None = None,
) -> dict[str, str]:
    """Generate an image synchronously. Blocks until the file is on disk.

    Typical latency is under 10 seconds. The PNG is written to the configured
    OUTPUT_DIR and the absolute path is returned.

    Args:
        prompt: Text description of the image to generate.
        model: "nano-banana" (Gemini 2.5 Flash Image — cheapest and fastest)
          or "imagen" (Imagen 4, higher quality, higher cost). Defaults to
          your configured default image model (run `visualgen-mcp init` to
          change).
        aspect_ratio: "1:1", "16:9", "9:16", "4:3", or "3:4". Defaults to
          your configured default image aspect ratio.
        negative_prompt: Optional text describing what to avoid. Ignored by
          Nano Banana; used by Imagen 4 when supplied.
    """
    cfg = _get_config()
    if model is None:
        model = cfg.default_image_model
    if aspect_ratio is None:
        aspect_ratio = cfg.default_image_aspect_ratio
    client = _get_client()
    try:
        return imagen.generate_image(
            client=client,
            prompt=prompt,
            model_alias=model,
            aspect_ratio=aspect_ratio,
            output_dir=cfg.output_dir,
            negative_prompt=negative_prompt,
        )
    except (ValueError, RuntimeError) as exc:
        return {"error": str(exc), "path": "", "model_used": ""}


@mcp.tool()
def list_images() -> list[dict[str, Any]]:
    """List every PNG file in the configured OUTPUT_DIR, newest first.

    Each entry has absolute path, size in bytes, and creation timestamp.
    """
    return imagen.list_images(_get_config().output_dir)


@mcp.tool()
def get_pricing() -> dict[str, Any]:
    """Return current published Gemini API pricing for the models this server uses.

    Rates are per-image for images and per-second for video. Pricing is
    hardcoded from the official docs (see the `source` field) and may drift;
    always verify before expensive operations.
    """
    return _PRICING


_PRICING: dict[str, Any] = {
    "last_updated": "2026-04-22",
    "currency": "USD",
    "source": "https://ai.google.dev/gemini-api/docs/pricing",
    "notes": [
        "No free tier for Veo. You are charged for successful generations only.",
        "Generated videos are deleted from Google's servers 48 hours after generation.",
        "Veo max clip duration is 8 seconds. Rates include audio.",
    ],
    "video": {
        "veo-3.1-generate-preview": {
            "tier": "standard",
            "per_second_usd": {"720p": 0.40, "1080p": 0.40, "4k": 0.60},
        },
        "veo-3.1-fast-generate-preview": {
            "tier": "fast",
            "per_second_usd": {"720p": 0.10, "1080p": 0.12, "4k": 0.30},
        },
        "veo-3.1-lite-generate-preview": {
            "tier": "lite",
            "per_second_usd": {"720p": 0.05, "1080p": 0.08},
            "notes": "4k not supported on lite tier.",
        },
    },
    "image": {
        "gemini-2.5-flash-image": {
            "alias": "nano-banana",
            "per_image_usd": 0.039,
            "notes": "Up to 1024x1024px. Discounted 50% via batch/flex modes.",
        },
        "imagen-4.0-fast-generate-001": {
            "alias": "imagen-fast",
            "per_image_usd": 0.02,
        },
        "imagen-4.0-generate-001": {
            "alias": "imagen",
            "per_image_usd": 0.04,
        },
        "imagen-4.0-ultra-generate-001": {
            "alias": "imagen-ultra",
            "per_image_usd": 0.06,
        },
    },
}


def run() -> None:
    """Start the MCP server over stdio."""
    # Log to stderr only — stdout is reserved for JSON-RPC framing in stdio mode.
    print("visualgen-mcp: starting on stdio", file=sys.stderr)
    mcp.run(transport="stdio")
