# Product shot

**When to use.** A clean, studio-style render of a specific product on a neutral background. Goes in features pages, pricing comparison cards, social proof sections.

**Defaults.** `model="imagen"` (product shots benefit from Imagen's higher fidelity and `negative_prompt` support). `aspect_ratio="1:1"` for card layouts, `4:3` for wider layouts.

**Prompt anatomy.**
- **Subject** — describe the product concretely. Material, color, shape, one or two distinguishing details.
- **Background** — *"clean white background"*, *"seamless gradient background"*, *"soft neutral gray studio backdrop"*. Keep it simple.
- **Lighting** — *"soft studio lighting"*, *"three-point lighting"*, *"single softbox from the upper left"*. Avoid dramatic lighting for product shots.
- **Composition** — *"centered"*, *"product hero angle"*, *"three-quarter view"*.
- **Negative prompt** — `text, watermark, hands, people, clutter, shadows on background, blurry edges`.

**Example calls.**

```
generate_image(
    prompt="a sleek stainless steel water bottle with a matte black lid, centered on a clean white background, soft studio lighting from the upper left, three-quarter view showing depth",
    model="imagen",
    aspect_ratio="1:1",
    negative_prompt="text, watermark, hands, people, clutter, shadows on background",
)
```

**Wiring into code.**

```jsx
<div className="aspect-square overflow-hidden rounded-lg bg-neutral-100">
  <img
    src="/generated/<filename>.png"
    alt="<product description>"
    className="h-full w-full object-contain"
  />
</div>
```

`object-contain` (not `object-cover`) is correct for product shots — you don't want to crop the product.
