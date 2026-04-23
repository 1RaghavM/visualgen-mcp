# `/visualgen` skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a Claude Code skill at `.claude/skills/visualgen/` that teaches Claude the visualgen-mcp decision tree, per-use-case prompt templates, cost-gating rules, and a `/visualgen <free text>` slash-command pipeline. Package it into the wheel so `visualgen-mcp init` can copy it into any user's project.

**Architecture:** Skill content is plain Markdown (`SKILL.md` + templates + reference files), edited directly in the repo at `.claude/skills/visualgen/`. Hatch's `force-include` bundles the tree into the wheel at `visualgen_mcp/_skill_data/`. The wizard resolves that path via `importlib.resources` and copies it into `<cwd>/.claude/skills/visualgen/`. A single drift-lint test verifies the skill's named tools and constants still match the server. TDD applies to wizard logic; for skill content, the drift lint runs red → green as files appear.

**Tech Stack:** Python 3.11, pytest, hatch, `importlib.resources`, stdlib `shutil` for the copy.

---

## Pre-flight

Before starting, verify the working tree is clean and you're on the feature branch.

```bash
git status
git branch --show-current
```

Expected: clean tree, branch `claude/ecstatic-haslett-9cabbb` (or whatever feature branch you're on).

Also verify the existing tests pass before you touch anything:

```bash
uv run pytest -q
```

Expected: all tests pass. If they don't, stop and fix that first — you can't tell what you broke if the baseline is already red.

---

## Task 1: Drift-lint test (red)

**Goal:** Write a single test file that pins down the shape of the skill — frontmatter, file presence, tool names matching the server, aspect ratios matching config. Run it. All assertions fail because no skill files exist yet.

**Files:**
- Create: `tests/test_skill_frontmatter.py`

**Step 1.1: Create the test file**

Write this file exactly:

```python
"""Drift lints for the /visualgen skill.

These tests don't cover runtime behavior — they catch drift between the skill's
Markdown content and the server's actual tool surface / config constants. When
someone renames a tool or removes an aspect ratio from config.py, the skill
silently going stale is the failure mode we want to prevent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / ".claude" / "skills" / "visualgen"

TEMPLATE_NAMES = [
    "hero-video",
    "hero-image",
    "background-loop",
    "product-shot",
    "illustration",
    "og-social-card",
]

REFERENCE_NAMES = ["prompt-anatomy", "cost-cheatsheet"]

SKILL_TOOL_NAMES = [
    "submit_video",
    "check_video",
    "list_videos",
    "generate_image",
    "list_images",
    "get_pricing",
]


def _read(path: Path) -> str:
    assert path.exists(), f"Missing: {path.relative_to(REPO)}"
    return path.read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a YAML-ish frontmatter block (name: value, description: value)."""
    assert text.startswith("---\n"), "Frontmatter must start with '---' on its own line"
    end = text.find("\n---\n", 4)
    assert end != -1, "Frontmatter must close with '---' on its own line"
    block = text[4:end]
    out: dict[str, str] = {}
    current_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line[0].isalpha() and ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            out[current_key] = value.strip()
        elif current_key is not None:
            out[current_key] = (out[current_key] + " " + line.strip()).strip()
    return out


def test_skill_md_exists_with_frontmatter() -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "visualgen"
    desc = fm.get("description", "")
    assert desc.startswith("Use whenever"), f"description must start with 'Use whenever', got: {desc[:60]!r}"


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_template_exists_with_h1(name: str) -> None:
    text = _read(SKILL_DIR / "templates" / f"{name}.md")
    first_line = text.splitlines()[0]
    assert first_line.startswith("# "), f"Template {name} must start with an h1 heading"


@pytest.mark.parametrize("name", REFERENCE_NAMES)
def test_reference_exists_with_h1(name: str) -> None:
    text = _read(SKILL_DIR / "reference" / f"{name}.md")
    first_line = text.splitlines()[0]
    assert first_line.startswith("# "), f"Reference {name} must start with an h1 heading"


def test_skill_mentions_all_tool_names() -> None:
    """Every tool the skill names must exist in server.py."""
    skill_text = _read(SKILL_DIR / "SKILL.md")
    server_text = _read(REPO / "src" / "visualgen_mcp" / "server.py")
    for tool in SKILL_TOOL_NAMES:
        assert tool in skill_text, f"SKILL.md should mention tool {tool!r}"
        assert re.search(rf"^def {re.escape(tool)}\(", server_text, re.MULTILINE), (
            f"Tool {tool!r} named in skill does not exist as `def {tool}(` in server.py"
        )


def test_skill_aspect_ratios_match_config() -> None:
    """Every aspect ratio the skill names must be in config.py's allowlists."""
    skill_text = _read(SKILL_DIR / "SKILL.md")
    config_text = _read(REPO / "src" / "visualgen_mcp" / "config.py")
    for ratio in ["16:9", "9:16", "1:1", "4:3", "3:4"]:
        if ratio in skill_text:
            assert ratio in config_text, (
                f"Skill mentions aspect ratio {ratio!r} but it's not in config.py"
            )


def test_skill_video_tiers_match_config() -> None:
    """Every Veo tier name the skill mentions must match VIDEO_MODELS keys."""
    skill_text = _read(SKILL_DIR / "SKILL.md")
    for tier in ["lite", "fast", "standard"]:
        assert tier in skill_text, f"SKILL.md should mention tier {tier!r}"
    # The server's keys are the source of truth; if this changes, update the list above.
    from visualgen_mcp.config import VIDEO_MODELS

    assert set(VIDEO_MODELS.keys()) == {"lite", "fast", "standard"}
```

**Step 1.2: Run and verify red**

```bash
uv run pytest tests/test_skill_frontmatter.py -v
```

Expected: Multiple failures — `Missing: .claude/skills/visualgen/SKILL.md` and similar for every template/reference file. This is the intended red state.

**Step 1.3: Commit**

```bash
git add tests/test_skill_frontmatter.py
git commit -m "Add drift-lint tests for /visualgen skill (red)"
```

---

## Task 2: Create `SKILL.md`

**Goal:** Write the authoritative skill body. After this, the frontmatter test passes but template/reference tests still fail.

**Files:**
- Create: `.claude/skills/visualgen/SKILL.md`

**Step 2.1: Create the directory**

```bash
mkdir -p .claude/skills/visualgen/templates .claude/skills/visualgen/reference
```

**Step 2.2: Write `SKILL.md`**

Create `.claude/skills/visualgen/SKILL.md` with this content exactly:

```markdown
---
name: visualgen
description: Use whenever generating, adding, or iterating on images or videos via the visualgen-mcp server (submit_video, check_video, generate_image, list_images, list_videos, get_pricing). Covers model selection, aspect-ratio decisions, prompt templates for web-design use cases (hero, background, product shot, illustration), cost-tier confirmation rules, and polling etiquette.
---

# visualgen

## When to use this skill

You are about to call any of the visualgen-mcp tools (`submit_video`, `check_video`, `list_videos`, `generate_image`, `list_images`, `get_pricing`), or the user asked you to add / generate / iterate on visuals (images or video) in a web-design context. Load this skill once, apply its rules for the rest of the session.

## Decision tree

- **Image or video?** If the user wants motion — a loop, a demo, a cinematic moment — use `submit_video`. Otherwise use `generate_image`. Still images are ~100× cheaper and ~10× faster; default to image unless motion is the point.
- **Aspect ratio.** Match the target surface:
  - Hero, banner, desktop landing → `16:9`
  - Mobile hero, story, reel → `9:16`
  - Avatar, icon, square card → `1:1`
  - Inline content illustration → `4:3` or `3:4`
  - OG / Twitter card → closest to 16:9 (native is 1200×630; the server doesn't support 1.91:1 so use `16:9` and crop in CSS)
- **Model tier — image.** Draft with `nano-banana` (`$0.039`/image). Upgrade to `imagen` when you need a `negative_prompt` or higher fidelity.
- **Model tier — video.** Draft with `lite` (`$0.05–$0.08`/sec). Ship with `fast` (`$0.10–$0.12`/sec at 720p/1080p). Only use `standard` (`$0.40`/sec) when the draft has proved the concept and the user has approved the higher cost.
- **`negative_prompt`.** Nano Banana ignores it. Imagen and Veo honor it. Use it when drafts keep including a specific unwanted element (text overlays, watermarks, specific colors, extra limbs, motion blur).
- **Image-to-video.** Pass `image_path` to `submit_video` when you want motion that matches an existing still — typically after generating a hero image and wanting a matching loop variant.

## Workflow rules

1. **Price once per session.** Call `get_pricing` on the first gated call, cache the numbers in your context, don't call it again in the same session unless the user asks.
2. **Gate expensive calls.** For Veo `standard` or any image-to-video call, state the estimated cost and ask the user to confirm before submitting. Use this exact format:

   > About to generate an 8s Veo standard clip at 1080p. Estimated cost: **$3.20**. Prompt: "<prompt>". Confirm to proceed? (yes / change / cancel)

   Response handling: `yes` → submit. `change` → return to prompt iteration. `cancel` → abort.
3. **Don't gate cheap calls.** Veo `fast` / `lite` and every `generate_image` proceed silently. Report what you generated after the fact.
4. **Batch gates.** If you plan to submit 2+ gated calls in one response (variations), show total cost once, gate once, submit all on confirmation.
5. **Poll politely.** After `submit_video`, call `check_video` at ~20s intervals. Typical completion is 30–120s. Don't tight-loop.
6. **Reference returned paths directly.** `check_video` and `generate_image` return absolute paths. Use them as-is in the code you write — don't copy, don't rename. The server put them in the user's configured `OUTPUT_DIR` on purpose.
7. **Iterate cheap first.** Always generate drafts at `lite` / `nano-banana` / `imagen-fast`, show the user, then re-run at higher tier only after concept approval.
8. **On `failed`.** Read the error. If it's a content-filter rejection, rewrite the prompt (remove brand names, specific people, potentially sensitive subjects) and resubmit. Don't retry the same prompt — it will just fail again.

## Tool reference

| Tool | When to use | Required args | Defaults |
|------|-------------|---------------|----------|
| `generate_image` | Still images — hero, product, illustration, OG card | `prompt` | `model=nano-banana`, `aspect_ratio=16:9` |
| `submit_video` | Any motion — returns `job_id` immediately | `prompt` | `model=fast`, `aspect_ratio=16:9`, `resolution=720p` |
| `check_video` | Poll a submitted job at ~20s intervals | `job_id` | n/a |
| `list_images` | Show the user what's already been generated | none | n/a |
| `list_videos` | Same, for video | none | n/a |
| `get_pricing` | Price the next gated call; call once per session | none | n/a |

## Pointers

- For prompt structure on a specific use case, read `templates/<use-case>.md`. Available: `hero-video`, `hero-image`, `background-loop`, `product-shot`, `illustration`, `og-social-card`.
- For the anatomy of a good prompt (subject → context → style → camera → lighting → negative), read `reference/prompt-anatomy.md`.
- For the full cost table and worked examples, read `reference/cost-cheatsheet.md`.

## `/visualgen` slash command

When the user invokes `/visualgen <free text>`, follow this pipeline:

1. **Parse intent.** Classify the free-text ask into exactly one template category (`hero-video`, `hero-image`, `background-loop`, `product-shot`, `illustration`, `og-social-card`). If ambiguous, pick the closest single one and state which you chose — do not generate multiples.
2. **No args.** If the user ran `/visualgen` alone, ask one question: *"What do you want to generate? (e.g., hero video, product shot, OG card)"*. Classify on their next message.
3. **Read the matched template.** Use its prompt-anatomy section to structure the prompt; do not paste the example prompts verbatim.
4. **Apply workflow rules 1–8** above. The cost gate fires when it fires.
5. **Wire into code if context implies a target.** If the user was mid-edit on a hero section, an empty `<img>`, OG meta tags, etc., reference the returned path directly in the file. Otherwise drop the path in a message and ask where to put it.

Edge cases:

- **Colon-separated prompt:** `/visualgen hero video: slow drone shot over a forest at dawn, calm cinematic` → everything after the first colon is the raw prompt. Still consult the template for model / aspect / resolution defaults and negative-prompt hints.
- **Inline tier hints:** `/visualgen hero video, cheap draft` → map `cheap draft` / `draft` / `preview` → `lite`, `final` / `ship` / `hero` → `fast` (or `standard` if the user explicitly says so and they've approved the cost).
- **Contradictions:** `/visualgen portrait hero 16:9` → pick the more specific / later token, state the choice in your first message back.
```

**Step 2.3: Run the frontmatter test**

```bash
uv run pytest tests/test_skill_frontmatter.py::test_skill_md_exists_with_frontmatter tests/test_skill_frontmatter.py::test_skill_mentions_all_tool_names tests/test_skill_frontmatter.py::test_skill_video_tiers_match_config tests/test_skill_frontmatter.py::test_skill_aspect_ratios_match_config -v
```

Expected: PASS for all four. Template/reference tests still fail — that's fine.

**Step 2.4: Commit**

```bash
git add .claude/skills/visualgen/SKILL.md
git commit -m "Add visualgen SKILL.md with decision tree and workflow rules"
```

---

## Task 3: `templates/hero-video.md`

**Files:**
- Create: `.claude/skills/visualgen/templates/hero-video.md`

**Step 3.1: Write the file**

```markdown
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
```

**Step 3.2: Commit**

```bash
git add .claude/skills/visualgen/templates/hero-video.md
git commit -m "Add hero-video template"
```

---

## Task 4: `templates/hero-image.md`

**Files:**
- Create: `.claude/skills/visualgen/templates/hero-image.md`

**Step 4.1: Write the file**

```markdown
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
```

**Step 4.2: Commit**

```bash
git add .claude/skills/visualgen/templates/hero-image.md
git commit -m "Add hero-image template"
```

---

## Task 5: `templates/background-loop.md`

**Files:**
- Create: `.claude/skills/visualgen/templates/background-loop.md`

**Step 5.1: Write the file**

```markdown
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
```

**Step 5.2: Commit**

```bash
git add .claude/skills/visualgen/templates/background-loop.md
git commit -m "Add background-loop template"
```

---

## Task 6: `templates/product-shot.md`

**Files:**
- Create: `.claude/skills/visualgen/templates/product-shot.md`

**Step 6.1: Write the file**

```markdown
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
```

**Step 6.2: Commit**

```bash
git add .claude/skills/visualgen/templates/product-shot.md
git commit -m "Add product-shot template"
```

---

## Task 7: `templates/illustration.md`

**Files:**
- Create: `.claude/skills/visualgen/templates/illustration.md`

**Step 7.1: Write the file**

```markdown
# Illustration

**When to use.** Inline content illustrations — blog headers, docs pages, marketing pages that want personality without photography. Usually appears in a set, so consistency matters.

**Defaults.** `model="imagen"` (stronger style adherence than Nano Banana). `aspect_ratio="4:3"` for most content blocks, `3:4` for vertical columns.

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
```

**Step 7.2: Commit**

```bash
git add .claude/skills/visualgen/templates/illustration.md
git commit -m "Add illustration template"
```

---

## Task 8: `templates/og-social-card.md`

**Files:**
- Create: `.claude/skills/visualgen/templates/og-social-card.md`

**Step 8.1: Write the file**

```markdown
# OG / social card

**When to use.** Open Graph or Twitter card image — the preview that shows up when someone shares a URL in Slack, iMessage, X, LinkedIn.

**Defaults.** `model="imagen"`, `aspect_ratio="16:9"`. Native OG spec is 1200×630 (≈1.91:1) which neither Imagen nor Veo supports; `16:9` is the closest supported, and the platforms crop to fit, so bias the important content to the center.

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
```

**Step 8.2: Commit**

```bash
git add .claude/skills/visualgen/templates/og-social-card.md
git commit -m "Add og-social-card template"
```

---

## Task 9: `reference/prompt-anatomy.md`

**Files:**
- Create: `.claude/skills/visualgen/reference/prompt-anatomy.md`

**Step 9.1: Write the file**

```markdown
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
```

**Step 9.2: Commit**

```bash
git add .claude/skills/visualgen/reference/prompt-anatomy.md
git commit -m "Add prompt-anatomy reference"
```

---

## Task 10: `reference/cost-cheatsheet.md`

**Files:**
- Create: `.claude/skills/visualgen/reference/cost-cheatsheet.md`

**Step 10.1: Write the file**

```markdown
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
```

**Step 10.2: Run the full lint suite**

```bash
uv run pytest tests/test_skill_frontmatter.py -v
```

Expected: all 11 tests PASS (1 frontmatter + 6 templates + 2 references + 2 drift).

**Step 10.3: Commit**

```bash
git add .claude/skills/visualgen/reference/cost-cheatsheet.md
git commit -m "Add cost-cheatsheet reference"
```

---

## Task 11: Package the skill into the wheel

**Goal:** When `visualgen-mcp` is installed via `uvx` or `pip`, the skill tree ships with it at a path `importlib.resources` can find. Without this, the wizard has nothing to copy from.

**Files:**
- Modify: `pyproject.toml`

**Step 11.1: Read current `[tool.hatch.build.targets.wheel]` block**

Confirm it currently reads:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/visualgen_mcp"]
```

**Step 11.2: Add `force-include`**

Append this block immediately after the existing `[tool.hatch.build.targets.wheel]` section:

```toml
[tool.hatch.build.targets.wheel.force-include]
".claude/skills/visualgen" = "visualgen_mcp/_skill_data"
```

This tells hatch: when building the wheel, copy the repo-relative `.claude/skills/visualgen/` tree into the installed package at `visualgen_mcp/_skill_data/`. That makes it reachable via `importlib.resources.files("visualgen_mcp") / "_skill_data"` at runtime.

**Step 11.3: Build the wheel and verify contents**

```bash
uv build --wheel
```

Expected: builds a wheel at `dist/visualgen_mcp-0.1.0-py3-none-any.whl` (or similar).

Inspect it:

```bash
unzip -l dist/visualgen_mcp-*.whl | grep _skill_data
```

Expected: lines listing `visualgen_mcp/_skill_data/SKILL.md`, every template, and both references — 9 files total.

**Step 11.4: Commit**

```bash
git add pyproject.toml
git commit -m "Bundle visualgen skill into the wheel via hatch force-include"
```

---

## Task 12: Wizard skill-install test (red)

**Goal:** Write tests for the new wizard behavior before implementing it. Follow the same `_feed` / `monkeypatch` patterns already in `tests/test_wizard.py`.

**Files:**
- Modify: `tests/test_wizard.py` (append new tests; don't touch existing ones)

**Step 12.1: Read the current bottom of `tests/test_wizard.py`**

You already have the file content in Task 12's modify target. The existing `test_run_defaults_path_writes_profile_and_prints_snippet` feeds six inputs for the six prompts (output_dir, video_tier, image_model, video_aspect, image_aspect, mcp_json_y_n). The new skill-install prompt comes AFTER the `.mcp.json` prompt, so it adds a seventh input.

**Step 12.2: Update the existing two `test_run_*` tests that walk the full wizard**

In `test_run_defaults_path_writes_profile_and_prints_snippet`, change:

```python
_feed(monkeypatch, ["", "", "", "", "", "n"])
```

to:

```python
_feed(monkeypatch, ["", "", "", "", "", "n", "n"])
```

In `test_run_merges_mcp_json_when_user_says_yes`, change:

```python
_feed(monkeypatch, ["", "", "", "", "", "y"])
```

to:

```python
_feed(monkeypatch, ["", "", "", "", "", "y", "n"])
```

The trailing `"n"` declines the new skill-install prompt. We're not testing the install yet here — these tests are about the pre-existing behavior still working.

**Step 12.3: Append new test cases**

Add these at the end of `tests/test_wizard.py`:

```python
def test_run_copies_skill_when_user_says_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    _feed_getpass(monkeypatch, "k")
    # 5 profile defaults, "n" to mcp.json, "y" to skill install
    _feed(monkeypatch, ["", "", "", "", "", "n", "y"])

    wizard.run()

    skill_root = tmp_path / ".claude" / "skills" / "visualgen"
    assert (skill_root / "SKILL.md").exists()
    assert (skill_root / "templates" / "hero-video.md").exists()
    assert (skill_root / "templates" / "og-social-card.md").exists()
    assert (skill_root / "reference" / "prompt-anatomy.md").exists()
    assert (skill_root / "reference" / "cost-cheatsheet.md").exists()

    # Byte-for-byte match against the source.
    from importlib import resources

    packaged = resources.files("visualgen_mcp") / "_skill_data" / "SKILL.md"
    assert (skill_root / "SKILL.md").read_bytes() == packaged.read_bytes()


def test_run_skips_skill_when_user_says_no(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    _feed_getpass(monkeypatch, "k")
    _feed(monkeypatch, ["", "", "", "", "", "n", "n"])

    wizard.run()

    skill_root = tmp_path / ".claude" / "skills" / "visualgen"
    assert not skill_root.exists(), "skill must not be installed when user declines"


def test_run_skill_install_skips_when_dest_exists_and_no_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    # Pre-create an existing skill dir with a sentinel file.
    skill_root = tmp_path / ".claude" / "skills" / "visualgen"
    skill_root.mkdir(parents=True)
    sentinel = skill_root / "SKILL.md"
    sentinel.write_text("DO NOT OVERWRITE")

    _feed_getpass(monkeypatch, "k")
    # 5 defaults, "n" to mcp.json, "y" to skill install, "n" to overwrite
    _feed(monkeypatch, ["", "", "", "", "", "n", "y", "n"])

    wizard.run()

    assert sentinel.read_text() == "DO NOT OVERWRITE"


def test_run_skill_install_overwrites_when_confirmed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    skill_root = tmp_path / ".claude" / "skills" / "visualgen"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text("stale")

    _feed_getpass(monkeypatch, "k")
    _feed(monkeypatch, ["", "", "", "", "", "n", "y", "y"])

    wizard.run()

    from importlib import resources

    packaged = resources.files("visualgen_mcp") / "_skill_data" / "SKILL.md"
    assert (skill_root / "SKILL.md").read_bytes() == packaged.read_bytes()
```

**Step 12.4: Run — all four new tests should fail**

```bash
uv run pytest tests/test_wizard.py -v
```

Expected: the four new `test_run_*skill*` tests fail (no such behavior yet). The two pre-existing `test_run_*` tests — now with the extra `"n"` input — should still pass since the old run() will just ignore the extra queued input.

Actually, check that more carefully — the existing `run()` reads only 6 inputs. The 7th queued input sits unused, which is fine. If it raises `StopIteration` for some reason, the tests will tell you.

**Step 12.5: Commit**

```bash
git add tests/test_wizard.py
git commit -m "Add failing tests for wizard skill-install prompt"
```

---

## Task 13: Implement wizard skill-install

**Files:**
- Modify: `src/visualgen_mcp/wizard.py`

**Step 13.1: Add imports**

At the top of `src/visualgen_mcp/wizard.py`, the imports currently include:

```python
import getpass
import json
import sys
from pathlib import Path
```

Add `shutil` and `importlib.resources` (the latter via `from importlib import resources`):

```python
import getpass
import json
import shutil
import sys
from importlib import resources
from pathlib import Path
```

**Step 13.2: Add the copy function**

Above `def run()` in `wizard.py`, add:

```python
def install_skill(dest_root: Path, *, overwrite: bool) -> str:
    """Copy the packaged skill tree to `dest_root / .claude/skills/visualgen`.

    Returns a status string:
      - "installed" on success
      - "skipped" when dest exists and overwrite is False
      - "error:<reason>" on any failure (permission, resource lookup, etc.)
    """
    target = dest_root / ".claude" / "skills" / "visualgen"
    if target.exists() and not overwrite:
        return "skipped"

    try:
        source = resources.files("visualgen_mcp") / "_skill_data"
    except (ModuleNotFoundError, FileNotFoundError) as exc:
        return f"error:cannot locate packaged skill: {exc}"

    try:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        # `resources.files` returns a Traversable; walk it manually.
        for entry in source.iterdir():
            _copy_traversable(entry, target / entry.name)
    except OSError as exc:
        return f"error:{exc}"

    return "installed"


def _copy_traversable(src: resources.abc.Traversable, dest: Path) -> None:
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for child in src.iterdir():
            _copy_traversable(child, dest / child.name)
    else:
        dest.write_bytes(src.read_bytes())
```

Why `_copy_traversable` and not `shutil.copytree`? Because `importlib.resources` returns a `Traversable`, which can point at a zip member (in a wheel) and has no filesystem path. We walk it manually to handle both cases.

**Step 13.3: Wire it into `run()`**

At the end of `run()`, just before the final `print("Paste this into any other MCP client config...")` line, add:

```python
    if confirm(
        "Install the /visualgen skill into .claude/skills/ in this project?",
        default=True,
    ):
        target_root = Path.cwd()
        skill_target = target_root / ".claude" / "skills" / "visualgen"
        overwrite = True
        if skill_target.exists():
            print(f"{skill_target} already exists.")
            overwrite = confirm("Overwrite?", default=False)
            if not overwrite:
                print("Left existing skill untouched.\n")
        if not skill_target.exists() or overwrite:
            result = install_skill(target_root, overwrite=True)
            if result == "installed":
                print(f"Installed /visualgen skill at {skill_target}\n")
            elif result == "skipped":
                print(f"Skipped: {skill_target} already exists.\n")
            else:
                reason = result.removeprefix("error:")
                print(f"Could not install skill: {reason}\n")
```

The nested `confirm("Overwrite?")` uses `default=False` — opt-in for destructive behavior. The `install_skill` call always passes `overwrite=True` at this point because we've already gated on the user's answer.

**Step 13.4: Run the wizard tests**

```bash
uv run pytest tests/test_wizard.py -v
```

Expected: all tests pass, including the four new ones.

If `test_run_skill_install_skips_when_dest_exists_and_no_overwrite` fails because the skill dir was pre-created empty, and the install_skill logic tried to copy into it — re-read Step 13.3 to confirm the outer `if skill_target.exists()` is gating correctly.

**Step 13.5: Run the full test suite**

```bash
uv run pytest -q
```

Expected: all tests pass.

**Step 13.6: Commit**

```bash
git add src/visualgen_mcp/wizard.py
git commit -m "Wire skill install into visualgen-mcp init wizard"
```

---

## Task 14: Verify end-to-end install via built wheel

**Goal:** Make sure the `importlib.resources` lookup actually works against the built wheel (not just the editable install). This catches packaging bugs that unit tests against the source tree won't catch.

**Step 14.1: Build a fresh wheel**

```bash
rm -rf dist/
uv build --wheel
```

**Step 14.2: Install it into a throwaway venv and run init**

```bash
python3 -m venv /tmp/visualgen-e2e
/tmp/visualgen-e2e/bin/pip install --quiet dist/visualgen_mcp-*.whl
mkdir -p /tmp/visualgen-e2e-project
```

Then interactively (this step is manual — automating TTY emulation isn't worth it):

```bash
cd /tmp/visualgen-e2e-project
/tmp/visualgen-e2e/bin/visualgen-mcp init
```

Walk through the prompts: enter a throwaway API key, accept all defaults, say `n` to `.mcp.json` merge (unless you want it here), say `y` to the skill-install prompt.

**Step 14.3: Verify the skill landed**

```bash
ls -R /tmp/visualgen-e2e-project/.claude/skills/visualgen/
```

Expected: `SKILL.md`, `templates/` with 6 files, `reference/` with 2 files.

```bash
diff <(cat .claude/skills/visualgen/SKILL.md) <(cat /tmp/visualgen-e2e-project/.claude/skills/visualgen/SKILL.md)
```

(Run from the repo root.)

Expected: no output — files match byte-for-byte.

**Step 14.4: Clean up**

```bash
rm -rf /tmp/visualgen-e2e /tmp/visualgen-e2e-project
```

No commit for this task — it's verification, not a code change.

---

## Task 15: README update

**Files:**
- Modify: `README.md`

**Step 15.1: Read the current `## Use with Claude Code` section**

It's currently at [README.md](README.md) around the section starting with "Either run `visualgen-mcp init` inside your project…". You're going to add a new subsection after the `/mcp` confirmation line.

**Step 15.2: Add the `### The /visualgen skill` subsection**

Immediately after the line that reads:

```markdown
Run `/mcp` inside Claude Code to confirm the server is connected. You should see `visualgen` listed with six tools.
```

Add:

```markdown

### The `/visualgen` skill

The server ships with a Claude Code skill that teaches Claude when to use each tool, how to structure prompts for common web-design asks, and when to confirm costs with you. If you ran `visualgen-mcp init`, it already offered to install it. Otherwise:

```bash
cd your-project
cp -r /path/to/visualgen-mcp/.claude/skills/visualgen ./.claude/skills/visualgen
```

Once installed, `/visualgen hero video, modern SaaS landing, calm mood` kicks off the whole pipeline in one shot — Claude picks the template, builds the prompt, submits the job, and wires the returned file into your code. You can also just ask for visuals in natural language — the skill auto-loads whenever Claude is about to call a visualgen-mcp tool.

The skill is opinionated about cost: Veo `standard` and image-to-video calls always ask you to confirm before spending. Draft tiers (`lite`, `fast`, Imagen Fast, Nano Banana) proceed silently.
```

**Step 15.3: Commit**

```bash
git add README.md
git commit -m "Document the /visualgen skill in README"
```

---

## Task 16: Final verification

**Step 16.1: Run the full test suite**

```bash
uv run pytest -q
```

Expected: all tests pass.

**Step 16.2: Lint and type-check**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Expected: no errors from any of the three. If `ruff format --check` complains, run `uv run ruff format` and commit any diffs in a follow-up commit.

**Step 16.3: Review the log**

```bash
git log --oneline origin/main..HEAD
```

Expected: a series of commits matching the task list, each small and focused.

**Step 16.4: Smoke the drift lint by breaking it deliberately**

A confidence check on the drift lint: temporarily rename a tool in `server.py`, run the skill lint, confirm it fails, revert.

```bash
# Temporarily break it
sed -i.bak 's/def submit_video/def submit_video_RENAMED/' src/visualgen_mcp/server.py
uv run pytest tests/test_skill_frontmatter.py::test_skill_mentions_all_tool_names -v
```

Expected: test fails with a clear message about `submit_video` not found.

Revert:

```bash
mv src/visualgen_mcp/server.py.bak src/visualgen_mcp/server.py
uv run pytest tests/test_skill_frontmatter.py::test_skill_mentions_all_tool_names -v
```

Expected: test passes again.

No commit for this task — it's verification.

---

## Done criteria

All of the following must be true before declaring this complete:

1. `.claude/skills/visualgen/` exists in the repo with `SKILL.md`, 6 templates, and 2 reference files.
2. `pyproject.toml` has the `force-include` block and `uv build --wheel` produces a wheel containing `visualgen_mcp/_skill_data/*.md`.
3. `uv run pytest -q` passes, including all 11 skill-frontmatter tests and the 4 new wizard tests.
4. `uv run ruff check .` and `uv run mypy` are clean.
5. `visualgen-mcp init` (tested against a built wheel in a throwaway venv) offers the skill-install prompt and copies files correctly on `y`.
6. README documents the skill under `## Use with Claude Code`.

## Out of scope

- Integration tests that actually call Veo/Imagen. The drift lints are the cheap equivalent.
- A separate `visualgen-mcp update-skill` CLI subcommand. If people need to refresh their installed skill, they can re-run `visualgen-mcp init` and confirm the overwrite prompt.
- Additional template categories (favicon, icon, texture). Add them later if the v1 pattern holds.
- Adaptation to non-visualgen-mcp servers. Per the brainstorming decision, this skill is visualgen-mcp-specific.
