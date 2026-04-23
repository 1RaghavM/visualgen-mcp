# Profile Wizard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `visualgen-mcp init`, an interactive setup flow that saves a user profile to `~/.config/visualgen-mcp/config.toml` and replaces the manual `.env` / `.mcp.json` editing the README asks for today.

**Architecture:** New `profile.py` module handles TOML I/O at an XDG path. New `wizard.py` module runs the interactive prompts and offers to merge `./.mcp.json`. Existing `Config.from_env()` grows a profile-loading step so env vars still override profile values (existing precedence preserved). Tool defaults in `server.py` become `None` sentinels that fall back to profile values at call time.

**Tech Stack:** Python 3.11+, stdlib `tomllib` for reads, `tomli-w` for writes, stdlib `input()` / `getpass.getpass()` / `json` for the wizard. Tests use `pytest` + `monkeypatch` + `capsys`. No new test deps.

**Design doc:** [docs/plans/2026-04-22-profile-wizard-design.md](2026-04-22-profile-wizard-design.md).

**TDD throughout** — follow @superpowers:test-driven-development. Before declaring done, follow @superpowers:verification-before-completion: run `uv run pytest`, `uv run ruff check`, `uv run mypy`.

---

## Task 1: Add `tomli-w` dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add the dep**

In `pyproject.toml`, inside `dependencies = [...]`, add `"tomli-w>=1.0.0",` after the `pydantic` line. Final block:

```toml
dependencies = [
    "mcp>=1.2.0",
    "google-genai>=0.3.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "tomli-w>=1.0.0",
]
```

**Step 2: Sync**

Run: `uv sync`
Expected: `tomli-w` resolves and installs; `uv.lock` updates.

**Step 3: Smoke-check**

Run: `uv run python -c "import tomli_w; import tomllib; print('ok')"`
Expected: `ok`

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "Add tomli-w dependency for profile TOML writes"
```

---

## Task 2: `profile.py` — XDG config path

**Files:**
- Create: `src/visualgen_mcp/profile.py`
- Test: `tests/test_profile.py`

**Step 1: Write the failing tests**

Create `tests/test_profile.py`:

```python
"""Tests for the user-level profile at ~/.config/visualgen-mcp/config.toml."""

from __future__ import annotations

from pathlib import Path

import pytest

from visualgen_mcp import profile


def test_config_path_honors_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert profile.config_path() == tmp_path / "visualgen-mcp" / "config.toml"


def test_config_path_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert profile.config_path() == tmp_path / ".config" / "visualgen-mcp" / "config.toml"


def test_config_path_ignores_empty_xdg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "   ")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert profile.config_path() == tmp_path / ".config" / "visualgen-mcp" / "config.toml"
```

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_profile.py -v`
Expected: `ModuleNotFoundError: No module named 'visualgen_mcp.profile'`

**Step 3: Write minimal implementation**

Create `src/visualgen_mcp/profile.py`:

```python
"""User-level profile stored at $XDG_CONFIG_HOME/visualgen-mcp/config.toml."""

from __future__ import annotations

import os
from pathlib import Path


def config_path() -> Path:
    """Resolve the profile path, honoring XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "visualgen-mcp" / "config.toml"
```

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_profile.py -v`
Expected: 3 passed.

**Step 5: Commit**

```bash
git add src/visualgen_mcp/profile.py tests/test_profile.py
git commit -m "Add profile.config_path with XDG support"
```

---

## Task 3: `profile.py` — `Profile` dataclass and `load_profile()`

**Files:**
- Modify: `src/visualgen_mcp/profile.py`
- Modify: `tests/test_profile.py`

**Step 1: Write the failing tests**

Append to `tests/test_profile.py`:

```python
def test_load_profile_returns_none_when_missing(tmp_path: Path) -> None:
    assert profile.load_profile(tmp_path / "nope.toml") is None


def test_load_profile_reads_all_fields(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        'api_key = "k-1"\n'
        'output_dir = "~/out"\n'
        "\n"
        "[defaults]\n"
        'video_tier = "standard"\n'
        'image_model = "imagen"\n'
        'video_aspect_ratio = "9:16"\n'
        'image_aspect_ratio = "1:1"\n'
    )
    prof = profile.load_profile(p)
    assert prof is not None
    assert prof.api_key == "k-1"
    assert prof.output_dir == "~/out"
    assert prof.video_tier == "standard"
    assert prof.image_model == "imagen"
    assert prof.video_aspect_ratio == "9:16"
    assert prof.image_aspect_ratio == "1:1"


def test_load_profile_missing_optional_fields(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('api_key = "only-key"\n')
    prof = profile.load_profile(p)
    assert prof is not None
    assert prof.api_key == "only-key"
    assert prof.output_dir is None
    assert prof.video_tier is None


def test_load_profile_ignores_unknown_keys(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        'api_key = "k"\n'
        'future_thing = "ignored"\n'
        "\n"
        "[defaults]\n"
        'future_default = "also-ignored"\n'
    )
    prof = profile.load_profile(p)
    assert prof is not None
    assert prof.api_key == "k"


def test_load_profile_malformed_raises_with_path(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text("this = is = not = toml")
    with pytest.raises(ValueError, match=str(p)):
        profile.load_profile(p)
```

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_profile.py -v`
Expected: 5 new failures (no `load_profile`, no `Profile`).

**Step 3: Write minimal implementation**

Replace the body of `src/visualgen_mcp/profile.py` with:

```python
"""User-level profile stored at $XDG_CONFIG_HOME/visualgen-mcp/config.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    """Values loaded from the TOML profile. All fields are optional."""

    api_key: str | None = None
    output_dir: str | None = None
    video_tier: str | None = None
    image_model: str | None = None
    video_aspect_ratio: str | None = None
    image_aspect_ratio: str | None = None


def config_path() -> Path:
    """Resolve the profile path, honoring XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "visualgen-mcp" / "config.toml"


def load_profile(path: Path | None = None) -> Profile | None:
    """Load the profile from disk. Returns None if the file doesn't exist.

    Raises ValueError (with the path) if the file exists but can't be parsed.
    """
    target = path if path is not None else config_path()
    if not target.exists():
        return None
    try:
        with target.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Malformed profile at {target}: {exc}") from exc
    defaults = data.get("defaults", {})
    return Profile(
        api_key=data.get("api_key"),
        output_dir=data.get("output_dir"),
        video_tier=defaults.get("video_tier"),
        image_model=defaults.get("image_model"),
        video_aspect_ratio=defaults.get("video_aspect_ratio"),
        image_aspect_ratio=defaults.get("image_aspect_ratio"),
    )
```

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_profile.py -v`
Expected: 8 passed.

**Step 5: Commit**

```bash
git add src/visualgen_mcp/profile.py tests/test_profile.py
git commit -m "Add Profile dataclass and load_profile"
```

---

## Task 4: `profile.py` — `save_profile()` with chmod

**Files:**
- Modify: `src/visualgen_mcp/profile.py`
- Modify: `tests/test_profile.py`

**Step 1: Write the failing tests**

Append to `tests/test_profile.py`:

```python
import stat


def test_save_profile_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "sub" / "config.toml"
    prof = profile.Profile(
        api_key="rt-key",
        output_dir="/out",
        video_tier="fast",
        image_model="nano-banana",
        video_aspect_ratio="16:9",
        image_aspect_ratio="16:9",
    )
    profile.save_profile(prof, p)
    loaded = profile.load_profile(p)
    assert loaded == prof


def test_save_profile_file_permissions_0600(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    profile.save_profile(profile.Profile(api_key="k"), p)
    mode = stat.S_IMODE(p.stat().st_mode)
    assert mode == 0o600


def test_save_profile_parent_dir_permissions_0700(tmp_path: Path) -> None:
    p = tmp_path / "visualgen-mcp" / "config.toml"
    profile.save_profile(profile.Profile(api_key="k"), p)
    mode = stat.S_IMODE(p.parent.stat().st_mode)
    assert mode == 0o700


def test_save_profile_omits_none_fields(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    profile.save_profile(profile.Profile(api_key="only-key"), p)
    contents = p.read_text()
    assert "api_key" in contents
    assert "output_dir" not in contents
    assert "[defaults]" not in contents  # no defaults table if all None
```

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_profile.py -v`
Expected: 4 new failures (`save_profile` not defined).

**Step 3: Write minimal implementation**

Append to `src/visualgen_mcp/profile.py`:

```python
import tomli_w  # noqa: E402 - grouped with other third-party imports logically


def save_profile(prof: Profile, path: Path | None = None) -> None:
    """Write the profile to disk with dir chmod 0700 and file chmod 0600."""
    target = path if path is not None else config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)

    data: dict[str, object] = {}
    if prof.api_key is not None:
        data["api_key"] = prof.api_key
    if prof.output_dir is not None:
        data["output_dir"] = prof.output_dir

    defaults: dict[str, object] = {}
    if prof.video_tier is not None:
        defaults["video_tier"] = prof.video_tier
    if prof.image_model is not None:
        defaults["image_model"] = prof.image_model
    if prof.video_aspect_ratio is not None:
        defaults["video_aspect_ratio"] = prof.video_aspect_ratio
    if prof.image_aspect_ratio is not None:
        defaults["image_aspect_ratio"] = prof.image_aspect_ratio
    if defaults:
        data["defaults"] = defaults

    with target.open("wb") as f:
        tomli_w.dump(data, f)
    os.chmod(target, 0o600)
```

Move the `import tomli_w` to the top with the other imports (put it on its own line under `import tomllib`).

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_profile.py -v`
Expected: 12 passed.

**Step 5: Commit**

```bash
git add src/visualgen_mcp/profile.py tests/test_profile.py
git commit -m "Add save_profile with 0600 file and 0700 dir permissions"
```

---

## Task 5: `Config.from_env()` merges profile; signpost error

**Files:**
- Modify: `src/visualgen_mcp/config.py`
- Modify: `tests/test_config.py`

**What changes:** `Config` grows four fields for tool-call defaults. `from_env()` reads the profile first, then lets env vars override. Missing-key error message becomes the signpost.

**Step 1: Write the failing tests**

Replace the `test_config_from_env_missing_key` test and add new tests. The full updated section at the bottom of `tests/test_config.py` should read:

```python
def test_config_from_env_missing_key_signposts_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Isolate the profile path so a real profile on the dev's machine doesn't leak in.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="visualgen-mcp init"):
        config.Config.from_env()


def test_config_from_env_empty_key_signposts_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="visualgen-mcp init"):
        config.Config.from_env()


def test_config_from_env_uses_profile_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from visualgen_mcp import profile

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    profile.save_profile(profile.Profile(api_key="profile-key"))
    c = config.Config.from_env()
    assert c.api_key == "profile-key"


def test_config_from_env_env_overrides_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from visualgen_mcp import profile

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    monkeypatch.chdir(tmp_path)
    profile.save_profile(profile.Profile(api_key="profile-key"))
    c = config.Config.from_env()
    assert c.api_key == "env-key"


def test_config_from_env_defaults_from_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from visualgen_mcp import profile

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.chdir(tmp_path)
    profile.save_profile(
        profile.Profile(
            api_key="k",
            video_tier="standard",
            image_model="imagen",
            video_aspect_ratio="9:16",
            image_aspect_ratio="1:1",
        )
    )
    c = config.Config.from_env()
    assert c.default_video_tier == "standard"
    assert c.default_image_model == "imagen"
    assert c.default_video_aspect_ratio == "9:16"
    assert c.default_image_aspect_ratio == "1:1"


def test_config_from_env_hardcoded_defaults_when_no_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    c = config.Config.from_env()
    assert c.default_video_tier == "fast"
    assert c.default_image_model == "nano-banana"
    assert c.default_video_aspect_ratio == "16:9"
    assert c.default_image_aspect_ratio == "16:9"
```

Delete the old `test_config_from_env_missing_key` and `test_config_from_env_empty_key` tests (they match on `"GEMINI_API_KEY"` which no longer appears in the error the same way — the new tests match on `"visualgen-mcp init"` which is the signpost).

Also update the existing `test_config_from_env_*` tests that set `GEMINI_API_KEY` without touching `XDG_CONFIG_HOME` to isolate: add `monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))` at the top of each. This prevents a real profile on a dev machine from leaking into the test.

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: the new tests fail (`default_video_tier` not on Config; error message doesn't match).

**Step 3: Write minimal implementation**

Replace the `Config` dataclass and `from_env` in `src/visualgen_mcp/config.py`:

```python
from visualgen_mcp import profile as profile_mod


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from env + profile."""

    api_key: str
    output_dir: Path
    default_video_tier: str
    default_image_model: str
    default_video_aspect_ratio: str
    default_image_aspect_ratio: str

    @classmethod
    def from_env(cls) -> Config:
        """Resolve config from env > profile > hard-coded defaults."""
        prof = profile_mod.load_profile()

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key and prof is not None and prof.api_key:
            api_key = prof.api_key.strip()
        if not api_key:
            raise ValueError(
                "No Gemini API key found. Run `visualgen-mcp init` to set up "
                "your profile, or set `GEMINI_API_KEY` in your environment "
                "(e.g. in `.env` or your `.mcp.json` env block)."
            )

        raw_dir = os.environ.get("OUTPUT_DIR", "").strip()
        if not raw_dir and prof is not None and prof.output_dir:
            raw_dir = prof.output_dir
        if not raw_dir:
            raw_dir = "./generated"
        output_dir = Path(raw_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            api_key=api_key,
            output_dir=output_dir,
            default_video_tier=(prof.video_tier if prof and prof.video_tier else "fast"),
            default_image_model=(
                prof.image_model if prof and prof.image_model else "nano-banana"
            ),
            default_video_aspect_ratio=(
                prof.video_aspect_ratio if prof and prof.video_aspect_ratio else "16:9"
            ),
            default_image_aspect_ratio=(
                prof.image_aspect_ratio if prof and prof.image_aspect_ratio else "16:9"
            ),
        )
```

Put the `from visualgen_mcp import profile as profile_mod` near the existing imports at the top (respect ruff's `I` isort rule — local imports last).

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: all tests pass.

**Step 5: Commit**

```bash
git add src/visualgen_mcp/config.py tests/test_config.py
git commit -m "Merge profile values into Config.from_env; signpost init command"
```

---

## Task 6: Thread profile defaults through `server.py` tool signatures

**Files:**
- Modify: `src/visualgen_mcp/server.py`

**Why:** MCP function signatures are inspected at import time. The hardcoded `model: str = "fast"` in `submit_video` would override the profile default. Switch to `None` sentinels and fall back to `Config` at call time.

**Step 1: No new tests required here.**

The existing tests cover `resolve_video_model`, `validate_video_params`, etc. Tool-dispatch tests don't exist in this repo (the tools depend on the google-genai SDK). We'll verify by reading the code and running `mypy` + the full test suite.

**Step 2: Modify `submit_video` signature and body**

Change the signature at `src/visualgen_mcp/server.py:55-62`:

```python
@mcp.tool()
def submit_video(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    resolution: str = "720p",
    negative_prompt: str | None = None,
    image_path: str | None = None,
) -> dict[str, Any]:
```

At the top of the function body (after the docstring), add:

```python
    cfg = _get_config()
    if model is None:
        model = cfg.default_video_tier
    if aspect_ratio is None:
        aspect_ratio = cfg.default_video_aspect_ratio
```

Then pass `model` / `aspect_ratio` to `veo.submit(...)` as before, and replace the `client = _get_client()` line below it with the existing call (the body logic otherwise doesn't change).

Note: `resolution` has no profile default per the design doc — keep the hardcoded `"720p"`.

**Step 3: Modify `generate_image` signature and body**

Change the signature at `src/visualgen_mcp/server.py:186-191`:

```python
@mcp.tool()
def generate_image(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    negative_prompt: str | None = None,
) -> dict[str, str]:
```

Add at the top of the function body:

```python
    cfg = _get_config()
    if model is None:
        model = cfg.default_image_model
    if aspect_ratio is None:
        aspect_ratio = cfg.default_image_aspect_ratio
```

Then pass `model` / `aspect_ratio` to `imagen.generate_image(...)` as before.

**Step 4: Update docstrings**

In each docstring, update the line describing the default to read, e.g. for `submit_video`:

> `model`: "lite" (cheapest), "fast" (good balance), or "standard" (highest quality). Defaults to your configured default video tier (run `visualgen-mcp init` to change).

Similarly for `aspect_ratio` and for `generate_image`'s `model` / `aspect_ratio`.

**Step 5: Run the full test suite and type-check**

Run: `uv run pytest -v && uv run mypy && uv run ruff check`
Expected: all pass.

**Step 6: Commit**

```bash
git add src/visualgen_mcp/server.py
git commit -m "Thread Config defaults through tool signatures via None sentinels"
```

---

## Task 7: `wizard.py` — prompt helpers and non-TTY guard

**Files:**
- Create: `src/visualgen_mcp/wizard.py`
- Test: `tests/test_wizard.py`

**Step 1: Write the failing tests**

Create `tests/test_wizard.py`:

```python
"""Tests for the interactive setup wizard."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest

from visualgen_mcp import wizard


def _feed(monkeypatch: pytest.MonkeyPatch, inputs: Iterable[str]) -> None:
    """Queue up a list of responses for input()."""
    it = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


def _feed_getpass(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setattr("getpass.getpass", lambda prompt="": value)


def test_prompt_required_rejects_empty_then_accepts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _feed(monkeypatch, ["", "  ", "real-value"])
    got = wizard.prompt_required("Key")
    assert got == "real-value"
    out = capsys.readouterr().out
    assert "required" in out.lower()


def test_prompt_with_default_empty_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, [""])
    assert wizard.prompt_with_default("Dir", default="~/out") == "~/out"


def test_prompt_with_default_user_value_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, ["/custom"])
    assert wizard.prompt_with_default("Dir", default="~/out") == "/custom"


def test_prompt_choice_empty_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, [""])
    assert wizard.prompt_choice("Tier", choices=["lite", "fast"], default="fast") == "fast"


def test_prompt_choice_invalid_then_valid(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _feed(monkeypatch, ["medium", "lite"])
    assert wizard.prompt_choice("Tier", choices=["lite", "fast"], default="fast") == "lite"
    out = capsys.readouterr().out
    assert "lite" in out and "fast" in out


def test_confirm_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, ["y"])
    assert wizard.confirm("Do it?", default=True) is True


def test_confirm_no(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, ["n"])
    assert wizard.confirm("Do it?", default=True) is False


def test_confirm_empty_returns_default_true(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, [""])
    assert wizard.confirm("Do it?", default=True) is True


def test_confirm_empty_returns_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _feed(monkeypatch, [""])
    assert wizard.confirm("Do it?", default=False) is False


def test_require_tty_exits_when_not_tty(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit) as exc:
        wizard.require_tty()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "interactive" in err.lower()


def test_require_tty_passes_when_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    wizard.require_tty()  # should not raise
```

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_wizard.py -v`
Expected: `ModuleNotFoundError: No module named 'visualgen_mcp.wizard'`.

**Step 3: Write minimal implementation**

Create `src/visualgen_mcp/wizard.py`:

```python
"""Interactive setup wizard for `visualgen-mcp init`."""

from __future__ import annotations

import getpass
import sys


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
```

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_wizard.py -v`
Expected: 11 passed.

**Step 5: Commit**

```bash
git add src/visualgen_mcp/wizard.py tests/test_wizard.py
git commit -m "Add wizard prompt helpers and TTY guard"
```

---

## Task 8: `wizard.py` — `.mcp.json` merge

**Files:**
- Modify: `src/visualgen_mcp/wizard.py`
- Modify: `tests/test_wizard.py`

**Step 1: Write the failing tests**

Append to `tests/test_wizard.py`:

```python
import json


def _entry() -> dict[str, object]:
    return {"command": "uvx", "args": ["visualgen-mcp"]}


def test_merge_mcp_json_creates_file(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    result = wizard.merge_mcp_json(path, _entry(), replace=False)
    assert result == "created"
    data = json.loads(path.read_text())
    assert data["mcpServers"]["visualgen"] == _entry()


def test_merge_mcp_json_adds_key_when_missing(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    path.write_text(json.dumps({"other": 1}))
    result = wizard.merge_mcp_json(path, _entry(), replace=False)
    assert result == "added"
    data = json.loads(path.read_text())
    assert data["other"] == 1
    assert data["mcpServers"]["visualgen"] == _entry()


def test_merge_mcp_json_preserves_other_servers(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "foo"}}}))
    wizard.merge_mcp_json(path, _entry(), replace=False)
    data = json.loads(path.read_text())
    assert data["mcpServers"]["other"] == {"command": "foo"}
    assert data["mcpServers"]["visualgen"] == _entry()


def test_merge_mcp_json_skips_when_present_and_replace_false(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    existing = {"command": "old", "args": []}
    path.write_text(json.dumps({"mcpServers": {"visualgen": existing}}))
    result = wizard.merge_mcp_json(path, _entry(), replace=False)
    assert result == "skipped"
    data = json.loads(path.read_text())
    assert data["mcpServers"]["visualgen"] == existing


def test_merge_mcp_json_replaces_when_replace_true(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    existing = {"command": "old", "args": []}
    path.write_text(json.dumps({"mcpServers": {"visualgen": existing}}))
    result = wizard.merge_mcp_json(path, _entry(), replace=True)
    assert result == "replaced"
    data = json.loads(path.read_text())
    assert data["mcpServers"]["visualgen"] == _entry()


def test_merge_mcp_json_invalid_json_returns_error(tmp_path: Path) -> None:
    path = tmp_path / ".mcp.json"
    path.write_text("{ not valid json")
    result = wizard.merge_mcp_json(path, _entry(), replace=False)
    assert result == "invalid"
    # File must NOT be overwritten.
    assert path.read_text() == "{ not valid json"
```

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_wizard.py -v`
Expected: 6 new failures (`merge_mcp_json` not defined).

**Step 3: Write minimal implementation**

Append to `src/visualgen_mcp/wizard.py`:

```python
import json
from pathlib import Path

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
```

Move the `import json` and `from pathlib import Path` up with the other imports at the top of the file (keep existing imports intact).

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_wizard.py -v`
Expected: 17 passed.

**Step 5: Commit**

```bash
git add src/visualgen_mcp/wizard.py tests/test_wizard.py
git commit -m "Add merge_mcp_json with replace-on-conflict semantics"
```

---

## Task 9: `wizard.py` — `run()` orchestration

**Files:**
- Modify: `src/visualgen_mcp/wizard.py`
- Modify: `tests/test_wizard.py`

**Step 1: Write the failing tests**

Append to `tests/test_wizard.py`:

```python
def test_run_defaults_path_writes_profile_and_prints_snippet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    # Order: api key (getpass), output dir, video tier, image model,
    # video aspect, image aspect, "offer .mcp.json merge? -> n"
    _feed_getpass(monkeypatch, "my-key")
    _feed(monkeypatch, ["", "", "", "", "", "n"])

    exit_code = wizard.run()
    assert exit_code == 0

    from visualgen_mcp import profile as profile_mod

    prof = profile_mod.load_profile()
    assert prof is not None
    assert prof.api_key == "my-key"
    assert prof.output_dir == "~/visualgen-output"
    assert prof.video_tier == "fast"
    assert prof.image_model == "nano-banana"

    out = capsys.readouterr().out
    assert "uvx" in out and "visualgen-mcp" in out  # snippet was printed


def test_run_merges_mcp_json_when_user_says_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    _feed_getpass(monkeypatch, "k")
    # 5 defaults empty, then "y" to merge
    _feed(monkeypatch, ["", "", "", "", "", "y"])

    wizard.run()
    mcp_path = tmp_path / ".mcp.json"
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    assert "visualgen" in data["mcpServers"]


def test_run_aborts_when_existing_profile_and_no_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from visualgen_mcp import profile as profile_mod

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    profile_mod.save_profile(profile_mod.Profile(api_key="existing"))

    _feed(monkeypatch, ["n"])  # "Overwrite? [y/N]" -> n
    exit_code = wizard.run()
    assert exit_code == 0

    # Profile unchanged.
    prof = profile_mod.load_profile()
    assert prof is not None
    assert prof.api_key == "existing"


def test_run_exits_1_when_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit) as exc:
        wizard.run()
    assert exc.value.code == 1
```

**Step 2: Run tests — expect fail**

Run: `uv run pytest tests/test_wizard.py -v`
Expected: 4 new failures (`run` not defined).

**Step 3: Write minimal implementation**

Append to `src/visualgen_mcp/wizard.py`:

```python
from visualgen_mcp import profile as profile_mod


VIDEO_TIER_CHOICES = ["lite", "fast", "standard"]
IMAGE_MODEL_CHOICES = ["nano-banana", "imagen"]
VIDEO_ASPECT_CHOICES = ["16:9", "9:16"]
IMAGE_ASPECT_CHOICES = ["1:1", "16:9", "9:16", "4:3", "3:4"]


_SNIPPET = {
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

    if confirm("Add visualgen-mcp to .mcp.json in the current directory?", default=True):
        mcp_path = Path.cwd() / ".mcp.json"
        entry = _SNIPPET["mcpServers"]["visualgen"]
        result = merge_mcp_json(mcp_path, entry, replace=False)
        if result == "skipped":
            existing = json.loads(mcp_path.read_text())["mcpServers"]["visualgen"]
            print(f"An entry for 'visualgen' already exists:\n{json.dumps(existing, indent=2)}")
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
```

Move the `from visualgen_mcp import profile as profile_mod` import to the top of the file with the other imports.

**Step 4: Run tests — expect pass**

Run: `uv run pytest tests/test_wizard.py -v`
Expected: 21 passed.

**Step 5: Type-check**

Run: `uv run mypy && uv run ruff check`
Expected: both pass.

**Step 6: Commit**

```bash
git add src/visualgen_mcp/wizard.py tests/test_wizard.py
git commit -m "Add wizard.run orchestration"
```

---

## Task 10: CLI dispatch for `init`

**Files:**
- Modify: `src/visualgen_mcp/__main__.py`

**Step 1: Rewrite**

Replace the contents of `src/visualgen_mcp/__main__.py`:

```python
"""Entry point: `python -m visualgen_mcp`, `uvx visualgen-mcp`, or `... init`."""

from __future__ import annotations

import sys

from dotenv import load_dotenv


def main() -> None:
    """Dispatch on argv: `init` runs the wizard, everything else runs the server."""
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        from visualgen_mcp.wizard import run

        raise SystemExit(run())

    load_dotenv()
    from visualgen_mcp.server import run as run_server

    run_server()


if __name__ == "__main__":
    main()
```

The wizard path does NOT call `load_dotenv()` — the wizard writes a user-level profile, not project env.

**Step 2: Smoke-test the dispatch**

Run: `uv run python -m visualgen_mcp init < /dev/null`
Expected: exits 1 with the "interactive terminal required" message (since `/dev/null` isn't a TTY).

Run: `GEMINI_API_KEY=stub uv run python -c "import sys; sys.argv = ['m']; from visualgen_mcp.__main__ import main"`

Actually, to confirm the import wiring works without starting the server, skip the runtime smoke test here and lean on the unit tests for wizard dispatch. Just verify the module imports cleanly:

Run: `uv run python -c "from visualgen_mcp import __main__; print('ok')"`
Expected: `ok`.

**Step 3: Commit**

```bash
git add src/visualgen_mcp/__main__.py
git commit -m "Dispatch 'init' subcommand to the wizard"
```

---

## Task 11: README — update setup instructions

**Files:**
- Modify: `README.md`

**Step 1: Rewrite the `## Configure` section**

Replace the existing `## Configure` section (currently telling users to `export GEMINI_API_KEY=...` or edit `.env`) with:

````markdown
## Configure

Run the interactive setup once. It saves your profile to `~/.config/visualgen-mcp/config.toml` (chmod 600) and optionally wires up `.mcp.json` in the current project directory.

```bash
uvx visualgen-mcp init
```

You'll be prompted for:

- **Gemini API key** — get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Veo requires a paid plan; Imagen and Nano Banana work on the free tier with stricter rate limits.
- **Output directory** — where generated PNGs and MP4s land. Defaults to `~/visualgen-output`.
- **Default video tier, image model, and aspect ratios** — used when Claude calls a tool without specifying these.

Re-run `visualgen-mcp init` any time to update the profile. Per-project overrides still work: a `GEMINI_API_KEY` in a local `.env` file or in `.mcp.json`'s `env` block takes precedence over the profile.
````

**Step 2: Update the `## Use with Claude Code` section**

The existing snippet tells users to put `GEMINI_API_KEY` in `env`. Simplify to the snippet the wizard produces:

````markdown
## Use with Claude Code

Either run `visualgen-mcp init` inside your project (it offers to write this for you), or add this to `.mcp.json` at the project root:

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

Run `/mcp` inside Claude Code to confirm the server is connected.
````

**Step 3: Update `.env.example` and `.mcp.json.example`**

Leave `.env.example` as-is (it remains useful for per-project overrides). Update `.mcp.json.example` so the primary example matches the new snippet (no `env` block in the default; include a commented block showing how to override).

**Step 4: Run the test suite once more**

Run: `uv run pytest -v && uv run mypy && uv run ruff check`
Expected: all pass.

**Step 5: Commit**

```bash
git add README.md .mcp.json.example
git commit -m "Update README and examples for visualgen-mcp init"
```

---

## Final verification

Per @superpowers:verification-before-completion, before calling this done:

```bash
uv run pytest -v
uv run mypy
uv run ruff check
```

Then end-to-end by hand:

```bash
# From a fresh shell with no GEMINI_API_KEY set:
unset GEMINI_API_KEY
rm -rf ~/.config/visualgen-mcp

uv run python -m visualgen_mcp init
# Walk through the prompts; verify the profile file at ~/.config/visualgen-mcp/config.toml
# and the .mcp.json merge if you chose yes.

# Verify server picks up the profile:
uv run python -c "from visualgen_mcp.config import Config; print(Config.from_env())"
# Should print a Config with your values — no GEMINI_API_KEY needed in env.
```

Push the branch and open a PR.
