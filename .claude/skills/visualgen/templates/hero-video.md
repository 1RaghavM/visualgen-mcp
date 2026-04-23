# Hero video

**When to use.** User wants a looping background video at the top of a landing page or marketing site. Typically autoplayed, muted, looping, 8 seconds.

**Defaults.** `model="fast"`, `aspect_ratio="16:9"`, `resolution="1080p"`. For the first draft, drop to `model="lite"` and `resolution="720p"`.

**Prompt anatomy.**
- **Subject + setting** — one clause: *"a slow drone shot over a misty forest canopy at dawn"*
- **Camera movement** — pick one: slow pan left/right, slow push-in, slow dolly-out, static wide shot, gentle orbit. Fast cuts make for bad loops.
- **Lighting / time of day** — golden hour, blue hour, overcast, night with city lights. Drives the mood more than any adjective.
- **Mood adjectives** — calm, cinematic, minimal, warm, moody. Pick 1–2. More than that confuses the model.
- **Negative prompt** — almost always: `text, watermark, fast cuts, jitter, motion blur, low quality`. Add `people` if the shot shouldn't have people, `logos` for brand-sensitive contexts.

**Example calls.**

Draft:
```
submit_video(
    prompt="slow drone shot over a misty forest canopy at dawn, soft golden light breaking through the trees, calm cinematic mood",
    model="lite",
    aspect_ratio="16:9",
    resolution="720p",
    negative_prompt="text, watermark, fast cuts, jitter, motion blur",
)
```

Final (gated — confirm cost first if `standard`):
```
submit_video(
    prompt="<same prompt>",
    model="fast",
    aspect_ratio="16:9",
    resolution="1080p",
    negative_prompt="text, watermark, fast cuts, jitter, motion blur",
)
```

**Wiring into code.** Once `check_video` returns `{status: "complete", path: "..."}`, drop the MP4 into the page as a background video:

```jsx
<video
  autoPlay
  muted
  loop
  playsInline
  className="absolute inset-0 h-full w-full object-cover"
  src="/generated/<filename-from-returned-path>.mp4"
/>
```

If the file isn't already under `public/`, either symlink it in or serve `OUTPUT_DIR` statically — the returned path is absolute and won't work as a URL.
