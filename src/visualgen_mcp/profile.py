"""User-level profile stored at $XDG_CONFIG_HOME/visualgen-mcp/config.toml."""

from __future__ import annotations

import os
from pathlib import Path


def config_path() -> Path:
    """Resolve the profile path, honoring XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "visualgen-mcp" / "config.toml"
