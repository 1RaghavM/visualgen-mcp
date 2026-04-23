# Background loop

**When to use.** Decorative video behind a section that isn't the hero. Pricing page, feature section, footer. Lower stakes, lower resolution, lower tier.

**Defaults.** `model="lite"`, `aspect_ratio="16:9"`, `resolution="720p"`. Default here is cheap on purpose — this is background noise, not a focal point.

**Prompt anatomy.**
- **Subject** — abstract or softly-focused, not a specific recognizable thing. Bokeh, gradients, particles, slow-moving clouds, abstract fluid.
- **Camera** — static or very slow drift. No pans, no push-ins.
- **Motion** — slow, ambient, loopable. Avoid anything with a clear start and end.
- **Lighting / color** — pick 1–2 dominant colors matching the section's palette.
- **Negative prompt** — `text, watermark, people, faces, logos, fast motion, hard cuts, flicker`.

**Example calls.**

Draft (same as final — no point going higher tier for a background):
```
submit_video(
    prompt="soft flowing gradient of deep navy and warm violet, slow ambient motion like ink dispersing in water, no subject, abstract, minimal",
    model="lite",
    aspect_ratio="16:9",
    resolution="720p",
    negative_prompt="text, watermark, people, faces, logos, fast motion, hard cuts, flicker",
)
```

**Wiring into code.**

```jsx
<section className="relative">
  <video
    autoPlay
    muted
    loop
    playsInline
    className="absolute inset-0 h-full w-full object-cover opacity-40"
    src="/generated/<filename>.mp4"
  />
  <div className="relative z-10 p-8">
    {/* section content */}
  </div>
</section>
```

The `opacity-40` is deliberate — backgrounds should not compete with the content on top.
