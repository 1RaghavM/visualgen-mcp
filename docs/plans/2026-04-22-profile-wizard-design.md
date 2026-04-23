# Profile wizard design

Date: 2026-04-22
Status: Approved, ready to plan

## Motivation

Today, users configure `visualgen-mcp` by manually editing `.env` or the `env` block of `.mcp.json`. This is friction at the worst possible moment — the first run — and requires the user to know which env vars matter. Replace it with an interactive `visualgen-mcp init` that collects settings once and stores them in a user-level profile.

## Decisions

Settled during brainstorming:

- **Single global profile** at `~/.config/visualgen-mcp/config.toml`. No named profiles, no per-project config beyond the existing `.env` override.
- **Wizard collects** API key, output directory, default video tier, default image model, default video/image aspect ratio. No API-key validation.
- **CLI surface** is one new subcommand: `visualgen-mcp init`. No `config show` / `config set` for now.
- **`.mcp.json` wiring** — wizard offers to merge an entry into `./.mcp.json` in the current directory, and always prints the snippet.
- **Friendly first-run error** — if the server starts with no API key from any source, the error points at `visualgen-mcp init`.

## Architecture

One new CLI entry point and one new module. The rest of the server is untouched.

New files:

- `src/visualgen_mcp/profile.py` — TOML read/write, XDG path resolution, file-permission enforcement.
- `src/visualgen_mcp/wizard.py` — interactive prompts and `.mcp.json` merge logic.
- `tests/test_profile.py`, `tests/test_wizard.py`.

Modified files:

- `src/visualgen_mcp/__main__.py` — dispatch on `sys.argv[1]`: `init` runs the wizard, anything else (or no argument) runs the server.
- `src/visualgen_mcp/config.py` — `Config.from_env()` merges profile values with env vars; no-API-key error gets the signpost.
- `pyproject.toml` — add `tomli-w` dep for writes. Reads use stdlib `tomllib`.
- `README.md` — replace the manual `.env` instructions with `visualgen-mcp init`.

## Config file schema

Path: `$XDG_CONFIG_HOME/visualgen-mcp/config.toml`, falling back to `~/.config/visualgen-mcp/config.toml`.

Directory permissions: `0700`. File permissions: `0600` (holds the API key).

```toml
api_key = "AIza..."
output_dir = "~/visualgen-output"

[defaults]
video_tier = "fast"          # lite | fast | standard
image_model = "nano-banana"  # nano-banana | imagen
video_aspect_ratio = "16:9"  # 16:9 | 9:16
image_aspect_ratio = "16:9"  # 1:1 | 16:9 | 9:16 | 4:3 | 3:4
```

Top-level keys for secret and path; nested `[defaults]` for tool-call defaults. Unknown keys are ignored on read (forward-compat). Missing keys fall back to hard-coded defaults in `config.py`.

## Loading precedence

When the server starts, values resolve in this order (first wins):

1. **Process env** — `GEMINI_API_KEY`, `OUTPUT_DIR` from the MCP client's `.mcp.json` `env` block or the user's shell.
2. **Profile TOML** — `~/.config/visualgen-mcp/config.toml`.
3. **Hard-coded defaults** — `output_dir = ./generated`, `video_tier = fast`, etc.

`.env` loading via `python-dotenv` happens before step 1, so a per-project `.env` still overrides the profile.

The `[defaults]` table only affects tool-call defaults when the caller omits the parameter. Explicit tool arguments always win over both env and profile.

If no API key resolves from any source, raise the signpost error:

> No Gemini API key found. Run `visualgen-mcp init` to set up your profile, or set `GEMINI_API_KEY` in your environment (e.g. in `.env` or your `.mcp.json` env block).

## Wizard flow

`visualgen-mcp init` runs interactively with `input()` / `getpass.getpass()` — no new deps beyond `tomli-w`.

```
$ visualgen-mcp init

Welcome to visualgen-mcp setup.
Config will be saved to ~/.config/visualgen-mcp/config.toml.

Gemini API key (get one at https://aistudio.google.com/apikey):
> [hidden input]

Output directory for generated images/videos [~/visualgen-output]:
>

Default video tier [fast] (lite/fast/standard):
>

Default image model [nano-banana] (nano-banana/imagen):
>

Default video aspect ratio [16:9] (16:9/9:16):
>

Default image aspect ratio [16:9] (1:1/16:9/9:16/4:3/3:4):
>

✓ Saved to ~/.config/visualgen-mcp/config.toml (chmod 600)

Add visualgen-mcp to .mcp.json in the current directory? [Y/n]
>

✓ Merged into ./.mcp.json

Or paste this into another MCP client config:

{
  "mcpServers": {
    "visualgen": {
      "command": "uvx",
      "args": ["visualgen-mcp"]
    }
  }
}

Done. Run /mcp inside Claude Code to confirm the server is connected.
```

Behavior:

- **API key is required.** Empty input re-prompts.
- Other fields accept empty → use the shown default.
- **Invalid choices** (e.g. `video_tier=medium`) re-prompt with the valid list; no crash.
- **Re-running `init` when a profile exists** → prompt *"Config exists at <path>. Overwrite? [y/N]"*. On `n`, exit without touching anything.
- **Non-TTY stdin** (piping, CI) → detect via `sys.stdin.isatty()` and exit 1 with a message pointing at manual env-var setup. Do not read piped input silently.

## `.mcp.json` merge

Target: `./.mcp.json` in the current working directory.

Canonical snippet (assumes PyPI install):

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

For from-source installs (no `uvx visualgen-mcp` available), substitute:

```json
{
  "command": "uv",
  "args": ["run", "python", "-m", "visualgen_mcp"],
  "cwd": "<absolute path to repo>"
}
```

Merge rules:

- **File doesn't exist** → create it with the snippet above.
- **File exists, no `mcpServers` key** → add the key with our entry.
- **File exists, `mcpServers.visualgen` already present** → show the existing entry and prompt *"Replace? [y/N]"*. Skip on `n`.
- **File exists but is invalid JSON** → don't overwrite. Print the snippet and tell the user to fix it by hand.
- **Preserve other `mcpServers` entries verbatim** — only the `visualgen` key is touched.
- Read → mutate dict → write back with `json.dumps(..., indent=2)`. JSON has no comments, so nothing to preserve on that front.

## Error handling

### Wizard

- **Can't write config directory** (permission denied, read-only FS) → print error + path; exit non-zero. No silent fallback.
- **Non-TTY stdin** → the message above; exit 1.
- **Ctrl-C mid-flow** → clean exit, no partial file written.

### Server boot (`Config.from_env()`)

- **No API key from any source** → the signpost error above.
- **Profile file exists but malformed TOML** → raise with file path and parser error. Don't silently fall back to env-only; the user should know the file is broken.
- **Profile has an invalid enum value** (e.g. `video_tier = "medium"`) → raise with the list of valid tiers and the config path, mirroring the existing validators in `config.py`.

## Testing

`tests/test_profile.py`:

- Round-trip: write → read → compare.
- XDG path resolution: honors `XDG_CONFIG_HOME`, falls back to `~/.config/`.
- File permissions after write are `0600`.
- Unknown keys in an existing file are preserved on read (forward-compat).
- Malformed TOML raises with the file path in the message.

`tests/test_wizard.py`:

- Drive prompts with `monkeypatch` on `input()` / `getpass.getpass()`; `capsys` for output assertions.
- Defaults path: empty inputs produce the expected TOML.
- Re-run with existing profile: "overwrite? N" exits without writing.
- Non-TTY: patch `sys.stdin.isatty()` to `False`; assert exit 1 and the correct message.
- `.mcp.json` merge scenarios, each with a fixture file: no file, empty file, existing unrelated servers, existing `visualgen` entry (replace Y and N), invalid JSON.

`tests/test_config.py` (extend existing):

- Precedence: profile-only, env-only, both (env wins).
- No source → the signpost message.
- `defaults.video_tier` from the profile feeds through to the tool default when no explicit arg is passed.

All unit tests; no network. Existing `pytest` + `pytest-asyncio` suffice — no new test deps.
