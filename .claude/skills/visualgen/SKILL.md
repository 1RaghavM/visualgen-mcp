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
