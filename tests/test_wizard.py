"""Tests for the interactive setup wizard."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

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


def test_run_defaults_path_writes_profile_and_prints_snippet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

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
    assert "uvx" in out and "visualgen-mcp" in out


def test_run_merges_mcp_json_when_user_says_yes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.chdir(tmp_path)

    _feed_getpass(monkeypatch, "k")
    _feed(monkeypatch, ["", "", "", "", "", "y"])

    wizard.run()
    mcp_path = tmp_path / ".mcp.json"
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    assert "visualgen" in data["mcpServers"]


def test_run_aborts_when_existing_profile_and_no_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from visualgen_mcp import profile as profile_mod

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    profile_mod.save_profile(profile_mod.Profile(api_key="existing"))

    _feed(monkeypatch, ["n"])
    exit_code = wizard.run()
    assert exit_code == 0

    prof = profile_mod.load_profile()
    assert prof is not None
    assert prof.api_key == "existing"


def test_run_exits_1_when_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(SystemExit) as exc:
        wizard.run()
    assert exc.value.code == 1
