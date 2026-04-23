# `/visualgen` skill design

Date: 2026-04-22
Status: Approved, ready to plan

## Motivation

`visualgen-mcp` exposes six tools, but nothing tells Claude when to use which one, how to structure a prompt for a hero video vs. a product shot, or when to pause and confirm a $3 Veo call with the user. Today that context lives in the author's head and in the README — Claude guesses, and the guesses drift from session to session. Ship a Claude Code skill that encodes the decision tree, prompt templates for common web-design asks, and cost-gating rules, so Claude does the right thing without being told each time. The skill also exposes a `/visualgen <free text>` slash command so users can invoke the whole pipeline in one shot.

## Decisions

Settled during brainstorming:

- **Scope: visualgen-mcp only.** The skill names `submit_video`, `check_video`, `generate_image`, etc. directly. No attempt to be portable across other image/video MCPs.
- **Invocation: inline-args slash command.** `/visualgen <free text>` parses intent, classifies into a template category, builds the prompt, calls the tool. Bare `/visualgen` asks one clarifying question.
- **Content: progressive disclosure.** A short authoritative `SKILL.md` plus per-use-case templates and reference files, loaded on demand.
- **Cost gate: tiered.** Silent for image generation and Veo `lite`/`fast` text-to-video. Confirmation required for Veo `standard` and for any image-to-video call regardless of tier.
- **Auto-trigger: on MCP tool-call intent.** Skill description is broad enough that Claude loads it whenever the user asks for visuals or Claude is about to call a visualgen-mcp tool.
- **Distribution: wizard integration.** The existing `visualgen-mcp init` wizard gains one prompt to copy the skill tree into the current project's `.claude/skills/`.

## Architecture

One new skill directory in this repo and one new wizard prompt. Nothing else in the server changes.

New files:

- `.claude/skills/visualgen/SKILL.md` — authoritative skill body with frontmatter, decision tree, workflow rules, and tool reference.
- `.claude/skills/visualgen/templates/hero-video.md`
- `.claude/skills/visualgen/templates/hero-image.md`
- `.claude/skills/visualgen/templates/background-loop.md`
- `.claude/skills/visualgen/templates/product-shot.md`
- `.claude/skills/visualgen/templates/illustration.md`
- `.claude/skills/visualgen/templates/og-social-card.md`
- `.claude/skills/visualgen/reference/prompt-anatomy.md`
- `.claude/skills/visualgen/reference/cost-cheatsheet.md`
- `tests/test_skill_frontmatter.py` — frontmatter + drift lints.

Modified files:

- `src/visualgen_mcp/wizard.py` — add the "install skill" prompt and copy logic.
- `tests/test_wizard.py` — one new test case for the skill-install prompt (both Y and N branches).
- `README.md` — add a short "What the skill does" section + fallback `cp -r` instructions for non-wizard installs.

## Skill layout

```
.claude/skills/visualgen/
  SKILL.md
  templates/
    hero-video.md
    hero-image.md
    background-loop.md
    product-shot.md
    illustration.md
    og-social-card.md
  reference/
    prompt-anatomy.md
    cost-cheatsheet.md
```

The skill is self-contained: nothing inside it depends on its install path, and nothing in the server depends on the skill existing.

## `SKILL.md` contents

Frontmatter:

```yaml
---
name: visualgen
description: Use whenever generating, adding, or iterating on images or videos via the visualgen-mcp server (submit_video, check_video, generate_image, list_images, list_videos, get_pricing). Covers model selection, aspect-ratio decisions, prompt templates for web-design use cases (hero, background, product shot, illustration), cost-tier confirmation rules, and polling etiquette.
---
```

Body sections, roughly 100 lines total:

1. **When to use this skill.** One paragraph restating the trigger.
2. **Decision tree.** Short prose + bullets covering:
   - Motion needed → video; otherwise image.
   - Aspect ratio by surface (hero/banner → `16:9`; mobile/story → `9:16`; avatar/icon → `1:1`; inline content → `4:3` or `3:4`).
   - Tier escalation: draft at the cheapest tier (`imagen-fast`, Veo `lite`), final at `imagen` or Veo `fast`, reserve `imagen-ultra` / Veo `standard` for approved concepts only.
   - `negative_prompt` usage (Imagen/Veo only; Nano Banana ignores it).
   - Image-to-video via `image_path` when motion should match an existing still.
3. **Workflow rules.** Numbered:
   1. Call `get_pricing` once per session before the first Veo call; cache in-context.
   2. Confirm cost before Veo `standard` and any image-to-video call.
   3. Proceed silently for Veo `fast`/`lite` and all image generation.
   4. Poll `check_video` at ~20s intervals, not tight loops.
   5. Reference returned absolute paths directly in code — no copy, no rename.
   6. On `failed` with a content-filter reason, rewrite the prompt and resubmit.
   7. Iterate at cheap tiers first, re-run at higher tier only after user approval.
4. **Tool reference.** Compact table: tool name, when-to-use, required args, defaults for optional args. Keyed to decisions, not just schema.
5. **Pointers.** One line each: "For `<use case>`, read `templates/<name>.md`. For prompt anatomy, read `reference/prompt-anatomy.md`. For costs, read `reference/cost-cheatsheet.md`."
6. **`/visualgen` slash command.** One paragraph describing the parse → classify → template → workflow pipeline.

No worked examples inline — those live in the templates.

## Template shape

Each `templates/*.md` is ~30–50 lines, same structure:

```markdown
# <use case>

**When to use.** <one sentence>

**Defaults.** model=<…>, aspect_ratio=<…>, resolution=<…>. Prefer <cheaper tier> for first drafts.

**Prompt anatomy.**
- Subject + setting
- Camera movement (video) or composition (image)
- Lighting / time of day
- Mood adjectives
- Negative prompt: <common unwanted elements>

**Example calls.**
- Draft: <submit_video(...) or generate_image(...)>
- Final: same prompt, upgraded tier — ask for cost confirmation if gated.

**Wiring into code.** <a small JSX/HTML snippet using the returned path>
```

Six templates total: `hero-video`, `hero-image`, `background-loop`, `product-shot`, `illustration`, `og-social-card`. Favicon/icon and texture cases are out of scope for v1 — they can be added later if demand shows up.

## Reference files

**`reference/prompt-anatomy.md`** — how to structure a prompt (subject → context → style → camera → lighting → negative), with a short "what Imagen/Veo tend to get wrong" list so Claude knows which failure modes to preempt with a negative prompt.

**`reference/cost-cheatsheet.md`** — flat table mirroring `get_pricing()`, plus three worked examples ("8s 1080p Veo standard = $3.20", "one Imagen-fast draft = $0.02", "three-variation draft pass at Veo lite = $1.20"). Drift from `get_pricing()` is caught by the frontmatter test.

## `/visualgen` slash-command behavior

Documented in `SKILL.md` under the slash-command section. Rules:

1. **Parse intent** from the free-text args. Classify into one template category. Ambiguous → pick closest, state the choice, don't generate multiples.
2. **No args** → ask: *"What do you want to generate? (e.g., hero video, product shot, OG card)"*. Classify on the next turn.
3. **Read the matched template.** Use its prompt-anatomy as a structural guide, not as copy source.
4. **Apply workflow rules 1–7.** Cost gate included.
5. **Wire into code** if context implies a target spot (mid-edit hero section, empty `<img>`, OG meta tags). Otherwise drop the path in a message and ask where to put it.

Edge cases:

- **Colon-separated prompt.** `/visualgen hero video: slow drone shot over a forest at dawn, calm cinematic` → tail after the first colon is the raw prompt; still consult the template for defaults.
- **Inline tier hints.** `/visualgen hero video, cheap draft` → map `cheap draft` to `lite`, same for `final`, `fast`, etc.
- **Contradictions.** `/visualgen portrait hero 16:9` → pick the more specific / later token, state the choice.

## Cost gate mechanics

**Silent (proceed, report after):**

- Any `generate_image` call.
- `submit_video` with `model="lite"` or `model="fast"`, no `image_path`.

**Gated (ask, wait for confirmation):**

- `submit_video` with `model="standard"`.
- `submit_video` with any `image_path` (image-to-video), regardless of tier.

**Gate format** — always the same three-word response set:

> About to generate an 8s Veo standard clip at 1080p. Estimated cost: **$3.20**. Prompt: "<prompt>". Confirm to proceed? (yes / change / cancel)

- `yes` → submit.
- `change` → return to prompt iteration.
- `cancel` → abort, don't submit.

**Batching.** If Claude plans to submit 2+ gated calls in the same response (variations), show the total cost once, gate once, submit all on confirmation.

**Pricing source.** On the first gated call in a session, call `get_pricing()` and use its returned rates. Cache in-context; don't re-call. Never hardcode rates in the gate message — they drift.

## Auto-trigger behavior

The frontmatter `description` above is written to match whenever:

- The user asks for visuals in a web-design context ("add a hero image", "generate a product shot", "make this background a video").
- Claude is about to call any visualgen-mcp tool.

Claude Code's skill-selection logic will load `SKILL.md` into context at that point. The templates and reference files are not loaded unless Claude explicitly reads them — that's the progressive-disclosure win.

## Wizard integration

`visualgen-mcp init` gains one prompt after the `.mcp.json` merge step:

```
Install the /visualgen skill into .claude/skills/ in this project? [Y/n]
> 
✓ Copied .claude/skills/visualgen/ (9 files)
```

Behavior:

- Source: the `.claude/skills/visualgen/` tree inside the installed `visualgen-mcp` package. Resolve via `importlib.resources` so it works for both `uvx` installs and editable installs.
- Destination: `<cwd>/.claude/skills/visualgen/`.
- If the destination already exists, prompt: *".claude/skills/visualgen/ already exists. Overwrite? [y/N]"*. On `n`, skip without touching anything.
- On `n` to the initial prompt, print a one-line pointer to the README section with manual `cp -r` instructions.
- Errors (permission denied, read-only FS) → print the error and skip, don't abort the rest of the wizard.

## Testing

**`tests/test_skill_frontmatter.py`** — new file, all unit tests, no network:

- Parse `SKILL.md` frontmatter; assert `name == "visualgen"` and `description` starts with `"Use whenever"`.
- Every `templates/*.md` and `reference/*.md` opens with a level-1 heading.
- Every tool name referenced in `SKILL.md` (`submit_video`, `check_video`, `generate_image`, `list_images`, `list_videos`, `get_pricing`) is defined as an `@mcp.tool()` in `src/visualgen_mcp/server.py`. Drift catcher.
- Every model tier and aspect ratio named in `SKILL.md` appears in `src/visualgen_mcp/config.py` (`VIDEO_MODELS`, aspect-ratio allowlists). Same idea.

**`tests/test_wizard.py`** — extend:

- New case for the skill-install prompt. On `y`, assert target tree exists and `SKILL.md` matches source byte-for-byte. On `n`, assert no tree was created.
- Destination-exists branch: pre-create the dir, answer `n` to overwrite, assert nothing was touched.

**Manual smoke test** — documented in the plan, not automated:

- `/visualgen hero video` in a fresh project → skill loads, Claude classifies, generates, wires a working `<video>` tag with the returned path.
- `/visualgen` alone → clarifying question fires.
- Explicit `/visualgen hero video, final 1080p standard` → cost gate fires with the three-word response set; `cancel` aborts cleanly.

**Out of scope.** No integration test that calls Veo/Imagen — the existing `tests/integration/` stays as-is. Those cost money and are flaky; the drift lints above are the cheap replacement for "does the skill still match the server".
