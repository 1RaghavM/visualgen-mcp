"""Interactive setup wizard for `visualgen-mcp init`."""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path

from visualgen_mcp import profile as profile_mod


def require_tty() -> None:
    """Exit 1 if stdin is not a TTY (piping, CI, etc.)."""
    if not sys.stdin.isatty():
        print(
            "`visualgen-mcp init` is interactive and requires a terminal.\n"
            "Set GEMINI_API_KEY in your environment instead, or write the "
            "profile manually at ~/.config/visualgen-mcp/config.toml.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def prompt_required(label: str, *, hidden: bool = False) -> str:
    """Prompt until the user enters a non-empty value."""
    while True:
        raw = (getpass.getpass if hidden else input)(f"{label}: ")
        value = raw.strip()
        if value:
            return value
        print(f"  {label} is required. Please enter a value.")


def prompt_with_default(label: str, *, default: str) -> str:
    """Prompt with a default shown in brackets; empty input returns the default."""
    raw = input(f"{label} [{default}]: ").strip()
    return raw if raw else default


def prompt_choice(label: str, *, choices: list[str], default: str) -> str:
    """Prompt for one of `choices`; re-prompt on invalid input."""
    options = "/".join(choices)
    while True:
        raw = input(f"{label} [{default}] ({options}): ").strip()
        value = raw if raw else default
        if value in choices:
            return value
        print(f"  Invalid choice {value!r}. Must be one of: {', '.join(choices)}")


def confirm(label: str, *, default: bool) -> bool:
    """Yes/no prompt. Empty input returns `default`."""
    hint = "Y/n" if default else "y/N"
    raw = input(f"{label} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


MergeResult = str  # "created" | "added" | "replaced" | "skipped" | "invalid"


def merge_mcp_json(path: Path, entry: dict[str, object], *, replace: bool) -> MergeResult:
    """Merge a 'visualgen' entry into `path`. Returns a status string."""
    if not path.exists():
        path.write_text(json.dumps({"mcpServers": {"visualgen": entry}}, indent=2) + "\n")
        return "created"

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return "invalid"
    if not isinstance(data, dict):
        return "invalid"

    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return "invalid"

    if "visualgen" in servers:
        if not replace:
            return "skipped"
        servers["visualgen"] = entry
        path.write_text(json.dumps(data, indent=2) + "\n")
        return "replaced"

    servers["visualgen"] = entry
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "added"


VIDEO_TIER_CHOICES = ["lite", "fast", "standard"]
IMAGE_MODEL_CHOICES = ["nano-banana", "imagen"]
VIDEO_ASPECT_CHOICES = ["16:9", "9:16"]
IMAGE_ASPECT_CHOICES = ["1:1", "16:9", "9:16", "4:3", "3:4"]

_SNIPPET: dict[str, object] = {
    "mcpServers": {
        "visualgen": {
            "command": "uvx",
            "args": ["visualgen-mcp"],
        }
    }
}


def run() -> int:
    """Run the interactive setup. Returns an exit code."""
    require_tty()

    path = profile_mod.config_path()
    if path.exists() and not confirm(
        f"Config exists at {path}. Overwrite?", default=False
    ):
        print("Aborted. No changes made.")
        return 0

    print("Welcome to visualgen-mcp setup.")
    print(f"Config will be saved to {path}.\n")

    print("Get a Gemini API key at https://aistudio.google.com/apikey")
    api_key = prompt_required("Gemini API key", hidden=True)

    output_dir = prompt_with_default(
        "Output directory for generated images/videos",
        default="~/visualgen-output",
    )
    video_tier = prompt_choice(
        "Default video tier", choices=VIDEO_TIER_CHOICES, default="fast"
    )
    image_model = prompt_choice(
        "Default image model", choices=IMAGE_MODEL_CHOICES, default="nano-banana"
    )
    video_aspect_ratio = prompt_choice(
        "Default video aspect ratio", choices=VIDEO_ASPECT_CHOICES, default="16:9"
    )
    image_aspect_ratio = prompt_choice(
        "Default image aspect ratio", choices=IMAGE_ASPECT_CHOICES, default="16:9"
    )

    profile_mod.save_profile(
        profile_mod.Profile(
            api_key=api_key,
            output_dir=output_dir,
            video_tier=video_tier,
            image_model=image_model,
            video_aspect_ratio=video_aspect_ratio,
            image_aspect_ratio=image_aspect_ratio,
        )
    )
    print(f"\nSaved to {path} (chmod 600)\n")

    servers = _SNIPPET["mcpServers"]
    assert isinstance(servers, dict)
    entry = servers["visualgen"]
    assert isinstance(entry, dict)

    if confirm("Add visualgen-mcp to .mcp.json in the current directory?", default=True):
        mcp_path = Path.cwd() / ".mcp.json"
        result = merge_mcp_json(mcp_path, entry, replace=False)
        if result == "skipped":
            existing = json.loads(mcp_path.read_text())["mcpServers"]["visualgen"]
            print(
                f"An entry for 'visualgen' already exists:\n{json.dumps(existing, indent=2)}"
            )
            if confirm("Replace?", default=False):
                result = merge_mcp_json(mcp_path, entry, replace=True)
        if result in {"created", "added", "replaced"}:
            print(f"{result.capitalize()} .mcp.json entry at {mcp_path}\n")
        elif result == "invalid":
            print(
                f"{mcp_path} exists but isn't valid JSON. Leaving it alone. "
                "Fix it and paste the snippet below manually.\n"
            )
        elif result == "skipped":
            print("Left existing entry untouched.\n")

    print("Paste this into any other MCP client config:\n")
    print(json.dumps(_SNIPPET, indent=2))
    print("\nDone. Run /mcp inside Claude Code to confirm the server is connected.")
    return 0
