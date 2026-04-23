# Illustration

**When to use.** Inline content illustrations — blog headers, docs pages, marketing pages that want personality without photography. Usually appears in a set, so consistency matters.

**Defaults.** `model="imagen"` (stronger style adherence than Nano Banana). `aspect_ratio="4:3"` for most content blocks, `3:4` for vertical columns. Skipping the Nano Banana draft step from SKILL rule 7 because this use case relies on `negative_prompt` (to suppress photorealism and clutter), which Nano Banana ignores.

**Prompt anatomy.**
- **Style first** — this is what makes a set consistent. Pick one and reuse it across every illustration: *"flat vector illustration"*, *"soft gradient illustration"*, *"isometric 3D illustration"*, *"hand-drawn line art with watercolor fill"*.
- **Subject** — the concept being illustrated.
- **Color palette** — name 2–4 specific colors. *"blue, coral, cream"*. Reuse across the set.
- **Composition** — *"centered subject with negative space around"*.
- **Negative prompt** — `text, watermark, photorealistic, cluttered, busy background`.

**Example calls.**

First illustration in the set:
```
generate_image(
    prompt="flat vector illustration of a person reading at a desk, soft gradients, color palette of muted teal, warm coral, and cream, centered subject with negative space around",
    model="imagen",
    aspect_ratio="4:3",
    negative_prompt="text, watermark, photorealistic, cluttered",
)
```

Second illustration in the same set (reuse the style / palette preamble):
```
generate_image(
    prompt="flat vector illustration of a plant growing in a pot next to a window, soft gradients, color palette of muted teal, warm coral, and cream, centered subject with negative space around",
    model="imagen",
    aspect_ratio="4:3",
    negative_prompt="text, watermark, photorealistic, cluttered",
)
```

Keep the first ~20 words of the prompt identical across the set. That's what makes them look like siblings.

**Wiring into code.**

```jsx
<img
  src="/generated/<filename>.png"
  alt="<illustration description>"
  className="mx-auto h-auto w-full max-w-md"
/>
```
