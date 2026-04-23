"""Interactive setup wizard for `visualgen-mcp init`."""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path


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
