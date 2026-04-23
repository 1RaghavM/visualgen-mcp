# Cost cheatsheet

Prices as of 2026-04-22 per `get_pricing()`. Always verify via the tool before an expensive run — the source of truth is Google's pricing page, which drifts.

## Flat table

| Model | Tier | Unit | Price |
|-------|------|------|-------|
| Veo 3.1 | standard | per second, 720p / 1080p | $0.40 |
| Veo 3.1 | standard | per second, 4k | $0.60 |
| Veo 3.1 | fast | per second, 720p | $0.10 |
| Veo 3.1 | fast | per second, 1080p | $0.12 |
| Veo 3.1 | fast | per second, 4k | $0.30 |
| Veo 3.1 | lite | per second, 720p | $0.05 |
| Veo 3.1 | lite | per second, 1080p | $0.08 |
| Imagen 4 | Fast | per image | $0.02 |
| Imagen 4 | Standard | per image | $0.04 |
| Imagen 4 | Ultra | per image | $0.06 |
| Nano Banana | — | per image | $0.039 |

## Worked examples

All Veo clips are 8 seconds (the server's hardcoded duration).

- **8s Veo lite @ 720p:** `8 × $0.05 = $0.40` per clip. The default draft. Cheap enough to iterate freely.
- **8s Veo fast @ 1080p:** `8 × $0.12 = $0.96` per clip. Good shipping default.
- **8s Veo standard @ 1080p:** `8 × $0.40 = $3.20` per clip. Gated — confirm with user first.
- **8s Veo standard @ 4k:** `8 × $0.60 = $4.80` per clip. Gated — confirm with user first.
- **One Imagen-fast draft:** $0.02. Effectively free for iteration.
- **Three Nano Banana variations:** `3 × $0.039 = $0.117`. Also effectively free.
- **Draft pass of 3 hero video candidates at lite 720p:** `3 × $0.40 = $1.20`. Not free but nowhere near gating threshold.

## Gating rules restated

- **Silent** (proceed, report after): any image; Veo `lite` or `fast` without `image_path`.
- **Gated** (ask first): Veo `standard`; any `submit_video` call with `image_path` (image-to-video).
- **Batch gate:** if ≥2 gated calls in one response, show total cost once, gate once.

## When you're not sure

Call `get_pricing()`. Cache the result in your context for the rest of the session.
