"""Tests for the imagen and veo providers. The google-genai client is mocked."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from visualgen_mcp.providers import imagen, veo

# ---------- imagen provider ----------


def _build_nano_banana_response(image_bytes: bytes) -> MagicMock:
    part = MagicMock()
    part.inline_data.data = image_bytes
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    return response


def _build_imagen_response(image_bytes: bytes) -> MagicMock:
    generated = MagicMock()
    generated.image.image_bytes = image_bytes
    response = MagicMock()
    response.generated_images = [generated]
    return response


def test_imagen_nano_banana_writes_png(tmp_path: Path) -> None:
    client = MagicMock()
    client.models.generate_content.return_value = _build_nano_banana_response(
        b"\x89PNG\r\n\x1a\nfake-nb"
    )
    result = imagen.generate_image(
        client=client,
        prompt="a cat",
        model_alias="nano-banana",
        aspect_ratio="16:9",
        output_dir=tmp_path,
    )
    out = Path(result["path"])
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG")
    assert result["model_used"] == "gemini-2.5-flash-image"
    call = client.models.generate_content.call_args
    assert call.kwargs["model"] == "gemini-2.5-flash-image"
    assert call.kwargs["contents"] == "a cat"


def test_imagen_imagen_writes_png(tmp_path: Path) -> None:
    client = MagicMock()
    client.models.generate_images.return_value = _build_imagen_response(
        b"\x89PNG\r\n\x1a\nfake-imagen"
    )
    result = imagen.generate_image(
        client=client,
        prompt="a dog",
        model_alias="imagen",
        aspect_ratio="1:1",
        output_dir=tmp_path,
    )
    out = Path(result["path"])
    assert out.exists()
    assert result["model_used"] == "imagen-4.0-generate-001"
    call = client.models.generate_images.call_args
    assert call.kwargs["model"] == "imagen-4.0-generate-001"
    assert call.kwargs["prompt"] == "a dog"


def test_imagen_rejects_invalid_aspect_ratio(tmp_path: Path) -> None:
    client = MagicMock()
    with pytest.raises(ValueError, match="aspect_ratio"):
        imagen.generate_image(
            client=client,
            prompt="a cat",
            model_alias="nano-banana",
            aspect_ratio="21:9",
            output_dir=tmp_path,
        )
    client.models.generate_content.assert_not_called()


def test_imagen_rejects_unknown_model(tmp_path: Path) -> None:
    client = MagicMock()
    with pytest.raises(ValueError, match="Unknown image model"):
        imagen.generate_image(
            client=client,
            prompt="a cat",
            model_alias="dalle",
            aspect_ratio="16:9",
            output_dir=tmp_path,
        )


def test_imagen_empty_imagen_response_raises(tmp_path: Path) -> None:
    client = MagicMock()
    response = MagicMock()
    response.generated_images = []
    client.models.generate_images.return_value = response
    with pytest.raises(RuntimeError, match="no images"):
        imagen.generate_image(
            client=client,
            prompt="a cat",
            model_alias="imagen",
            aspect_ratio="16:9",
            output_dir=tmp_path,
        )


def test_imagen_nano_banana_no_inline_data_raises(tmp_path: Path) -> None:
    client = MagicMock()
    part = MagicMock()
    part.inline_data = None
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    client.models.generate_content.return_value = response
    with pytest.raises(RuntimeError, match="no image data"):
        imagen.generate_image(
            client=client,
            prompt="a cat",
            model_alias="nano-banana",
            aspect_ratio="16:9",
            output_dir=tmp_path,
        )


def test_imagen_list_images_empty(tmp_path: Path) -> None:
    assert imagen.list_images(tmp_path) == []


def test_imagen_list_images_returns_newest_first(tmp_path: Path) -> None:
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    # Force b's mtime to be later than a's
    import os
    import time

    time.sleep(0.01)
    os.utime(b, None)
    entries = imagen.list_images(tmp_path)
    assert [Path(e["path"]).name for e in entries] == ["b.png", "a.png"]
    assert entries[0]["size_bytes"] == 1


def test_imagen_list_images_ignores_non_png(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"a")
    (tmp_path / "b.mp4").write_bytes(b"b")
    (tmp_path / "c.txt").write_text("c")
    entries = imagen.list_images(tmp_path)
    assert len(entries) == 1
    assert Path(entries[0]["path"]).name == "a.png"


# ---------- veo provider ----------


def test_veo_submit_returns_operation_and_model() -> None:
    client = MagicMock()
    operation = MagicMock()
    client.models.generate_videos.return_value = operation
    result = veo.submit(
        client=client,
        prompt="a waterfall",
        tier="fast",
        aspect_ratio="16:9",
        resolution="720p",
    )
    assert result["operation"] is operation
    assert result["model_id"] == "veo-3.1-fast-generate-preview"
    call = client.models.generate_videos.call_args
    assert call.kwargs["model"] == "veo-3.1-fast-generate-preview"
    assert call.kwargs["prompt"] == "a waterfall"
    assert "image" not in call.kwargs


def test_veo_submit_passes_image_when_given(tmp_path: Path) -> None:
    img_path = tmp_path / "frame.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    client = MagicMock()
    client.models.generate_videos.return_value = MagicMock()
    veo.submit(
        client=client,
        prompt="a waterfall",
        tier="fast",
        aspect_ratio="16:9",
        resolution="720p",
        image_path=str(img_path),
    )
    call = client.models.generate_videos.call_args
    assert "image" in call.kwargs


def test_veo_submit_missing_image_raises(tmp_path: Path) -> None:
    client = MagicMock()
    with pytest.raises(FileNotFoundError):
        veo.submit(
            client=client,
            prompt="a waterfall",
            tier="fast",
            aspect_ratio="16:9",
            resolution="720p",
            image_path=str(tmp_path / "does-not-exist.png"),
        )


def test_veo_submit_rejects_4k_on_lite() -> None:
    client = MagicMock()
    with pytest.raises(ValueError, match="lite"):
        veo.submit(
            client=client,
            prompt="a waterfall",
            tier="lite",
            aspect_ratio="16:9",
            resolution="4k",
        )
    client.models.generate_videos.assert_not_called()


def test_veo_poll_returns_refreshed_operation() -> None:
    client = MagicMock()
    initial: Any = MagicMock(name="initial")
    refreshed: Any = MagicMock(name="refreshed")
    client.operations.get.return_value = refreshed
    assert veo.poll(client=client, operation=initial) is refreshed
    client.operations.get.assert_called_once_with(initial)


def test_veo_download_saves_mp4(tmp_path: Path) -> None:
    client = MagicMock()
    video_obj = MagicMock()
    generated = MagicMock()
    generated.video = video_obj
    operation = MagicMock()
    operation.response.generated_videos = [generated]

    path = veo.download(
        client=client,
        operation=operation,
        output_dir=tmp_path,
        tier="fast",
    )
    client.files.download.assert_called_once_with(file=video_obj)
    video_obj.save.assert_called_once_with(path)
    assert path.startswith(str(tmp_path))
    assert path.endswith(".mp4")
    assert "veo-fast" in Path(path).name


def test_veo_download_no_videos_raises(tmp_path: Path) -> None:
    client = MagicMock()
    operation = MagicMock()
    operation.response.generated_videos = []
    with pytest.raises(RuntimeError, match="no videos"):
        veo.download(
            client=client,
            operation=operation,
            output_dir=tmp_path,
            tier="fast",
        )


def test_veo_download_no_response_raises(tmp_path: Path) -> None:
    client = MagicMock()
    operation = MagicMock()
    operation.response = None
    with pytest.raises(RuntimeError, match="without a response"):
        veo.download(
            client=client,
            operation=operation,
            output_dir=tmp_path,
            tier="fast",
        )


def test_veo_extract_error_uses_message() -> None:
    op = MagicMock()
    op.error.message = "quota exceeded"
    assert veo.extract_error(op) == "quota exceeded"


def test_veo_extract_error_no_error_returns_fallback() -> None:
    op = MagicMock()
    op.error = None
    assert "no error message" in veo.extract_error(op)


def test_veo_list_videos_empty(tmp_path: Path) -> None:
    assert veo.list_videos(tmp_path) == []


def test_veo_list_videos_ignores_non_mp4(tmp_path: Path) -> None:
    (tmp_path / "a.mp4").write_bytes(b"a")
    (tmp_path / "b.png").write_bytes(b"b")
    entries = veo.list_videos(tmp_path)
    assert len(entries) == 1
    assert Path(entries[0]["path"]).name == "a.mp4"
