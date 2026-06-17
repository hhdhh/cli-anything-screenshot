"""End-to-end smoke tests for the CLI entry point.

These exercise the full Click group as a user would, with a fully mocked
screencapture / sips. They are the closest thing to an E2E test the harness
can run on a headless CI box.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from cli_anything.screenshot import screenshot_cli as C


# ── helpers ────────────────────────────────────────────────────────────────

def _screencapture_factory():
    """Mock screencapture that writes fake PNG bytes to the dest."""
    def factory(cmd, **kwargs):
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG_FAKE" + b"\x00" * 1024)
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m
    return factory


def _sips_factory():
    """Mock sips that writes the output file in the requested format."""
    def factory(cmd, **kwargs):
        dst = Path(cmd[cmd.index("--out") + 1])
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"FAKE_" + b"\x00" * 256)
        m = MagicMock()
        m.returncode = 0
        return m
    return factory


# ── tests ─────────────────────────────────────────────────────────────────

def test_capture_full_writes_a_file(tmp_path):
    out = tmp_path / "shot.png"
    runner = CliRunner()
    with patch("subprocess.run", side_effect=_screencapture_factory()):
        result = runner.invoke(C.cli, [
            "capture", "full",
            "--no-sounds",
            "--output", str(out),
        ])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert out.stat().st_size > 0


def test_capture_region_emits_json(tmp_path):
    out = tmp_path / "r.png"
    runner = CliRunner()
    with patch("subprocess.run", side_effect=_screencapture_factory()):
        result = runner.invoke(C.cli, [
            "--json", "capture", "region",
            "-x", "10", "-y", "20", "-w", "300", "-h", "400",
            "--output", str(out),
        ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["format"] == "png"
    assert data["source"] == "region"
    assert data["region"] == {"x": 10, "y": 20, "w": 300, "h": 400}
    assert data["path"] == str(out)


def test_capture_full_records_to_session(tmp_path, monkeypatch):
    """A successful capture must be appended to bounded session history."""
    fake_session = tmp_path / "session.json"
    monkeypatch.setattr(
        "cli_anything.screenshot.utils.screencapture_backend.DEFAULT_SESSION_FILE",
        fake_session,
    )
    monkeypatch.setattr(
        "cli_anything.screenshot.core.session.DEFAULT_SESSION_FILE",
        fake_session,
    )
    runner = CliRunner()
    with patch("subprocess.run", side_effect=_screencapture_factory()):
        for i in range(3):
            result = runner.invoke(C.cli, [
                "capture", "full",
                "--no-sounds",
                "--output", str(tmp_path / f"shot{i}.png"),
            ])
            assert result.exit_code == 0, result.output

    assert fake_session.exists()
    data = json.loads(fake_session.read_text())
    assert len(data["history"]) == 3
    assert data["state"]["total_captures"] == 3


def test_convert_uses_sips_with_chosen_format(tmp_path):
    src = tmp_path / "in.png"
    src.write_bytes(b"\x89PNG_FAKE")
    runner = CliRunner()
    with patch("shutil.which", return_value="/usr/bin/sips"):
        with patch("subprocess.run", side_effect=_sips_factory()):
            result = runner.invoke(C.cli, [
                "--json", "convert", str(src),
                "--format", "jpg",
            ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["format"] == "jpg"
    assert data["output"].endswith(".jpg")


def test_config_set_then_get_round_trip(tmp_path):
    cfg_file = tmp_path / "config.json"
    runner = CliRunner()
    result = runner.invoke(C.cli, [
        "--config", str(cfg_file),
        "config", "set", "play_sounds", "false",
    ])
    assert result.exit_code == 0, result.output
    result = runner.invoke(C.cli, [
        "--config", str(cfg_file),
        "--json", "config", "get", "play_sounds",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["play_sounds"] is False


def test_unknown_command_exits_nonzero():
    runner = CliRunner()
    result = runner.invoke(C.cli, ["nonexistent-cmd"])
    assert result.exit_code != 0


def test_help_lists_all_command_groups():
    runner = CliRunner()
    result = runner.invoke(C.cli, ["--help"])
    assert result.exit_code == 0
    for grp in ("capture", "displays", "windows", "convert", "config", "session"):
        assert grp in result.output, f"missing group in help: {grp}"


def test_capture_full_help_lists_real_options():
    """screenshot-harness capture full has its own flag set (not minimax TTS)."""
    runner = CliRunner()
    result = runner.invoke(C.cli, ["capture", "full", "--help"])
    assert result.exit_code == 0
    for opt in ("--output", "--display", "--cursor", "--sounds", "--format"):
        assert opt in result.output, f"missing option in capture full help: {opt}"


def test_displays_runs_without_real_display(monkeypatch):
    """list_displays has a fallback so the CLI never crashes on headless."""
    from cli_anything.screenshot.utils import screencapture_backend as B
    monkeypatch.setattr(C, "list_displays",
                        lambda: [{"index": 1, "name": "Mock", "resolution": "1x1", "main": True}])
    runner = CliRunner()
    result = runner.invoke(C.cli, ["--json", "displays"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data[0]["name"] == "Mock"
