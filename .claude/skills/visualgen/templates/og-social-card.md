# OG / social card

**When to use.** Open Graph or Twitter card image — the preview that shows up when someone shares a URL in Slack, iMessage, X, LinkedIn.

**Defaults.** `model="imagen"`, `aspect_ratio="16:9"`. Native OG spec is 1200×630 (≈1.91:1) which neither Imagen nor Veo supports; `16:9` is the closest supported, and the platforms crop to fit, so bias the important content to the center. Skipping the Nano Banana draft step from SKILL rule 7 because this use case relies on `negative_prompt` (to keep text and clutter out of the card), which Nano Banana ignores.

**Prompt anatomy.**
- **Subject** — a single visual that reads at a glance. OG cards are often seen at thumbnail size.
- **Composition** — *"centered composition with key visual in the middle third"*. Platforms may crop the edges.
- **Text-safe zone** — leave ~20% padding from every edge for text overlay you'll add in code or an image editor. *"lots of negative space around the subject"*.
- **Style** — match the site's visual identity. If the site is photographic, make the OG card photographic. If illustrated, illustrated.
- **Negative prompt** — `text, watermark, low quality, busy, cluttered edges`. Text in the generated image fights with text overlays you'll add later.

**Example calls.**

```
generate_image(
    prompt="centered composition of a single bright blue paper airplane on a soft cream background, flat illustration style, lots of negative space around the subject for text overlay, minimal",
    model="imagen",
    aspect_ratio="16:9",
    negative_prompt="text, watermark, busy, cluttered edges",
)
```

**Wiring into code.**

Next.js `app/opengraph-image.tsx` or a static file referenced by meta tags:

```html
<meta property="og:image" content="/generated/<filename>.png" />
<meta property="og:image:width" content="1792" />
<meta property="og:image:height" content="1008" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="/generated/<filename>.png" />
```

If you need text on the card (article title, site name), overlay it with CSS or generate a separate text layer — don't ask the model to render text, it almost always mangles it.
