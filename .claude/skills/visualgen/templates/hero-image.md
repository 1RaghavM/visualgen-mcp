# Hero image

**When to use.** Landing-page still hero. Cheaper and faster than a hero video; motion isn't adding anything; or the site ships to users who'd be annoyed by autoplay.

**Defaults.** `model="nano-banana"` for drafts, `model="imagen"` for final. `aspect_ratio="16:9"` for desktop, `9:16` for mobile-first.

**Prompt anatomy.**
- **Subject + setting** — one clear clause. Hero images work best with a clear focal point.
- **Composition** — *"wide shot with negative space on the left"*, *"centered composition"*, *"off-center with rule of thirds"*. Tell the model where the text will go.
- **Style** — photographic, illustrative, 3D render, isometric, minimal line art. Pick one.
- **Lighting** — soft natural light, studio softbox, dramatic rim light, golden hour.
- **Negative prompt** (Imagen only, not Nano Banana) — `text, watermark, low quality, blurry`.

**Example calls.**

Draft:
```
generate_image(
    prompt="a minimalist product photo of a ceramic coffee mug on a linen tablecloth, morning light from the left, lots of negative space in the top-right for headline text, soft shadows",
    model="nano-banana",
    aspect_ratio="16:9",
)
```

Final (adds negative prompt):
```
generate_image(
    prompt="<same prompt>",
    model="imagen",
    aspect_ratio="16:9",
    negative_prompt="text, watermark, low quality, blurry",
)
```

**Wiring into code.**

```jsx
<img
  src="/generated/<filename-from-returned-path>.png"
  alt="<describe the image>"
  className="h-full w-full object-cover"
/>
```

Same caveat as hero-video: the returned path is absolute; serve `OUTPUT_DIR` statically or copy the file into the project's static dir.
