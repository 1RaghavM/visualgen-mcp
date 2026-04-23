# Prompt anatomy

The order matters. These models weight earlier tokens more heavily, so put the most important decisions first.

## Universal structure

1. **Subject** — what's in the shot. One clear noun phrase.
2. **Context / setting** — where and what's around the subject.
3. **Style** — photographic, illustrated, 3D, vector, isometric, etc.
4. **Camera / composition** — angle, distance, framing, movement (for video).
5. **Lighting** — time of day, quality (soft / hard), direction.
6. **Mood** — 1–2 adjectives max. *calm*, *cinematic*, *minimal*, *dramatic*.
7. **Negative prompt** — what to exclude (Imagen and Veo only; Nano Banana ignores this).

## What Imagen and Veo tend to get wrong

- **Text rendering.** Both models are terrible at spelling. Don't ask for text unless you're okay with garbled output. Add text as a CSS overlay or in an image editor.
- **Hands and faces at small scale.** If a person is small in the frame, expect mangled hands. Either make the subject larger or frame so hands aren't visible.
- **Specific brand likenesses.** Refused by the content filter. Don't name brands or public figures.
- **Counting.** "Exactly three apples" will give you two or five. Use it as a hint, not a spec.
- **Reading direction.** "On the left" is unreliable; it's more like a ~60% bias. If layout matters, generate and re-roll until you get what you want.
- **Consistent characters across generations.** Each call is independent. For a set with the same character, you'll get variations every time. Use image-to-video (`image_path`) to lock motion to a specific still.

## When to use a negative prompt

Use it when drafts keep producing something specific you don't want. General "high quality" negatives are cargo-cult — they don't help. Specific exclusions do:

- **Text / watermarks:** `text, watermark, logo, signature` — always include for UI imagery.
- **People in scenic shots:** `people, person, humans, figures` — when you want an empty landscape.
- **Style leakage:** `photorealistic` (for stylized work), `cartoon` (for photorealistic work).
- **Composition leakage:** `blurry, low quality, motion blur, jpeg artifacts` — when drafts keep looking soft.

## Prompt length

Keep it under ~60 words. Longer prompts start fighting with themselves. If you need more specificity, prefer a tight prompt + a specific `negative_prompt` over a verbose positive prompt.
