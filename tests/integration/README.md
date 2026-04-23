# Integration tests

These tests hit the real Gemini API. They are **not** run in CI. Running them costs real money — each video is at least a few cents and a full Veo Standard run is a few dollars.

## When to run

- Before cutting a release.
- After bumping `google-genai` or changing anything in `providers/`.
- When you suspect an SDK or model-ID drift.

## How to run

Set a real API key and point the tests at a scratch directory:

```bash
export GEMINI_API_KEY=your_real_key
export OUTPUT_DIR=/tmp/visualgen-integration
mkdir -p "$OUTPUT_DIR"

uv run pytest tests/integration/ -v
```

The tests use small, cheap configurations (Nano Banana for images, Veo 3.1 Lite at 720p for video) but they are not free. Budget roughly $0.50 for a full run.

Files land in `$OUTPUT_DIR` and are not cleaned up automatically — check them manually and delete when done.
