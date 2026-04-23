# visualgen-mcp

An MCP server that lets Claude Code generate images and short videos via Google's Gemini API (Imagen 4 for stills, Veo 3.1 for video).

## Why this exists

I was building websites with Claude Code and kept hitting the same gap. Claude would design a great layout, then say "add your hero image here." I'd go generate one somewhere else, come back, wire it up, iterate, repeat. The context switching was the whole cost. So I built this MCP server to close the loop. Claude writes the prompt, the server hits Veo or Imagen, the file lands in the project directory, and Claude references it in the code it's already writing. One session, no handoffs.

I'm open-sourcing it because other people are solving the same problem, and nobody should have to build this twice.

## What it does

Six tools, exposed over stdio:

- `submit_video(prompt, model, aspect_ratio, resolution, negative_prompt?, image_path?)` — submit a Veo 3.1 job. Returns a `job_id` instantly.
- `check_video(job_id)` — poll a job. When the video is ready, the server downloads it and returns the path.
- `list_videos()` — list MP4s in the output directory, newest first.
- `generate_image(prompt, model, aspect_ratio, negative_prompt?)` — synchronous image generation (typically under 10s). Returns the PNG path.
- `list_images()` — list PNGs in the output directory.
- `get_pricing()` — return current Gemini rates so Claude can warn you before expensive runs.

## What it costs

Gemini API rates as of 2026-04-22. Verify at the [official pricing page](https://ai.google.dev/gemini-api/docs/pricing) before production use.

| Model                              | Cost                                         |
|------------------------------------|----------------------------------------------|
| Veo 3.1 Standard (720p / 1080p)    | $0.40 / second                               |
| Veo 3.1 Standard (4k)              | $0.60 / second                               |
| Veo 3.1 Fast (720p)                | $0.10 / second                               |
| Veo 3.1 Fast (1080p)               | $0.12 / second                               |
| Veo 3.1 Fast (4k)                  | $0.30 / second                               |
| Veo 3.1 Lite (720p)                | $0.05 / second                               |
| Veo 3.1 Lite (1080p)               | $0.08 / second                               |
| Imagen 4 Fast                      | $0.02 / image                                |
| Imagen 4 Standard                  | $0.04 / image                                |
| Imagen 4 Ultra                     | $0.06 / image                                |
| Gemini 2.5 Flash Image (Nano Banana) | $0.039 / image                             |

There is no free tier for Veo. You pay for every successful generation. A failed or filtered generation is not billed. An 8-second Veo 3.1 Standard clip at 1080p is about $3.20. Call `get_pricing` before big runs if you're not sure.

## Install

For end users:

```bash
uvx visualgen-mcp
```

For contributors (from source):

```bash
git clone https://github.com/1RaghavM/visualgen-mcp.git
cd visualgen-mcp
uv sync
uv run python -m visualgen_mcp
```

## Configure

Run the interactive setup once. It saves your profile to `~/.config/visualgen-mcp/config.toml` (chmod 600) and optionally wires up `.mcp.json` in the current project directory.

```bash
uvx visualgen-mcp init
```

You'll be prompted for:

- **Gemini API key** — get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Veo requires a paid plan; Imagen and Nano Banana work on the free tier but with stricter rate limits.
- **Output directory** — where generated PNGs and MP4s land. Defaults to `~/visualgen-output`. The server creates it if it doesn't exist, and tool responses return absolute paths so Claude can reference the files in the code it writes.
- **Default video tier, image model, and aspect ratios** — used when Claude calls a tool without specifying these.

Re-run `visualgen-mcp init` any time to update the profile. Per-project overrides still work: a `GEMINI_API_KEY` or `OUTPUT_DIR` set in a local `.env` file or in `.mcp.json`'s `env` block takes precedence over the profile.

## Use with Claude Code

Either run `visualgen-mcp init` inside your project (it offers to write this for you), or add this to `.mcp.json` at the root of your project:

```json
{
  "mcpServers": {
    "visualgen": {
      "command": "uvx",
      "args": ["visualgen-mcp"]
    }
  }
}
```

The server reads your API key and defaults from `~/.config/visualgen-mcp/config.toml`. If you want to override them for a specific project, set `GEMINI_API_KEY` or `OUTPUT_DIR` in `.mcp.json`'s `env` block — env vars take precedence over the profile.

Run `/mcp` inside Claude Code to confirm the server is connected. You should see `visualgen` listed with six tools.

### The `/visualgen` skill

The server ships with a Claude Code skill that teaches Claude when to use each tool, how to structure prompts for common web-design asks, and when to confirm costs with you. If you ran `visualgen-mcp init`, it already offered to install it. Otherwise:

```bash
cd your-project
cp -r /path/to/visualgen-mcp/.claude/skills/visualgen ./.claude/skills/visualgen
```

Once installed, `/visualgen hero video, modern SaaS landing, calm mood` kicks off the whole pipeline in one shot — Claude picks the template, builds the prompt, submits the job, and wires the returned file into your code. You can also just ask for visuals in natural language — the skill auto-loads whenever Claude is about to call a visualgen-mcp tool.

The skill is opinionated about cost: Veo `standard` and any image-to-video call always ask you to confirm before spending. Everything else — all image generation plus Veo `lite`/`fast` text-to-video — proceeds silently.

## Use with other MCP clients

Claude Desktop uses the same pattern. Add an entry under `mcpServers` in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows). Any stdio-transport MCP client that supports tool calls works. There is no HTTP or auth layer — the server is intended for local use.

## Example session

A real run from a landing-page project. Elided lines marked `...`.

```
> Build me a hero video loop for the top of the page. Something that suggests "city at night, calm, slow."

I'll generate that with the visualgen server.

  submit_video(
    prompt="A slow drone shot over a city skyline at night, warm window lights,
            occasional headlights tracing streets below, calm mood, cinematic",
    model="fast",
    aspect_ratio="16:9",
    resolution="1080p"
  )
  → { "job_id": "f3c1...", "status": "submitted", "model": "veo-3.1-fast-generate-preview",
      "estimated_seconds": 60 }

I'll check back in a minute.

  check_video("f3c1...")
  → { "status": "pending", "elapsed_seconds": 25 }

  ... wait ...

  check_video("f3c1...")
  → { "status": "complete",
      "path": "/Users/.../landing/generated/veo-fast-20260422T191203Z.mp4",
      "duration_seconds": 8.0 }

Writing it into the hero section:

  Edit: src/components/Hero.tsx
    <video
      autoPlay
      muted
      loop
      playsInline
      className="absolute inset-0 h-full w-full object-cover"
      src="/generated/veo-fast-20260422T191203Z.mp4"
    />
```

One prompt, one generation, file in the project, code updated.

## Tool reference

### `submit_video`

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `prompt` | `str` | (required) | Video description. |
| `model` | `str` | `"fast"` | `"lite"`, `"fast"`, or `"standard"`. |
| `aspect_ratio` | `str` | `"16:9"` | `"16:9"` or `"9:16"`. |
| `resolution` | `str` | `"720p"` | `"720p"`, `"1080p"`, `"4k"`. `"4k"` rejected for `"lite"`. |
| `negative_prompt` | `str \| None` | `None` | Text describing what to avoid. |
| `image_path` | `str \| None` | `None` | Absolute path to a PNG/JPEG/WebP starting frame. |

Returns `{"job_id": str, "status": "submitted", "model": str, "estimated_seconds": int}`.

### `check_video`

| Param | Type | Default |
|-------|------|---------|
| `job_id` | `str` | (required) |

Returns one of:

- `{"status": "pending", "elapsed_seconds": int}`
- `{"status": "complete", "path": str, "duration_seconds": float}`
- `{"status": "failed", "error": str}`

### `list_videos`

No parameters. Returns `list[{"path": str, "size_bytes": int, "created_at": str}]`, newest first.

### `generate_image`

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `prompt` | `str` | (required) | Image description. |
| `model` | `str` | `"nano-banana"` | `"nano-banana"` or `"imagen"`. |
| `aspect_ratio` | `str` | `"16:9"` | `"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`. |
| `negative_prompt` | `str \| None` | `None` | Ignored by Nano Banana. |

Returns `{"path": str, "model_used": str}`.

### `list_images`

No parameters. Returns `list[{"path": str, "size_bytes": int, "created_at": str}]`, newest first.

### `get_pricing`

No parameters. Returns a dict of current rates per model, a `last_updated` date, and a link to the source. Hardcoded — the server does not call an API for this.

## Limits and gotchas

- Veo clips are capped at 8 seconds. This server always requests 8 seconds.
- There is no free tier for Veo. Every successful generation is billed.
- Generated videos are deleted from Google's servers 48 hours after generation. Download them (via `check_video`) within that window.
- The job store is in-memory. If you restart the server, pending jobs are lost. See the TODO in `src/visualgen_mcp/jobs.py` for the SQLite migration path.
- Some prompts are rejected by Google's content filters. You get `{"status": "failed", ...}` back, not a crash.
- Nano Banana (`gemini-2.5-flash-image`) is faster and cheaper than Imagen 4 but does not accept a `negative_prompt`. Use Imagen 4 when you need one.
- `list_videos` and `list_images` only see files in `OUTPUT_DIR`. They do not recurse or cross directories.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
