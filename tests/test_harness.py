"""Tests for the screenshot harness (no real screen capture required).

Covers:
- backend: find / config / format validation
- backend: capture_full / capture_region / capture_window with mocked screencapture
- backend: convert_image with mocked sips
- session: in-memory state + atomic write
- CLI: arg parsing, error path, JSON output
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from cli_anything.screenshot.utils import screencapture_backend as B
from cli_anything.screenshot.core import session as S
from cli_anything.screenshot import screenshot_cli as C


# ── backend: discovery & config ──────────────────────────────────────────────

def test_find_screencapture_returns_path():
    assert B.find_screencapture() == "/usr/sbin/screencapture"


def test_find_screencapture_raises_when_missing(tmp_path):
    with patch.object(B, "SCREENCAPTURE_BIN", "/nonexistent/screencapture"):
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="not found"):
                B.find_screencapture()


def test_load_config_returns_defaults_when_missing(tmp_path):
    cfg = B.load_config(tmp_path / "nope.json")
    assert cfg["default_format"] == "png"
    assert cfg["play_sounds"] is True


def test_save_and_load_config_round_trip(tmp_path):
    cfg_file = tmp_path / "cfg.json"
    B.save_config({"default_format": "jpg", "play_sounds": False}, cfg_file)
    loaded = B.load_config(cfg_file)
    assert loaded["default_format"] == "jpg"
    assert loaded["play_sounds"] is False
    # Other keys still come from DEFAULTS
    assert loaded["include_cursor"] is False


def test_valid_formats_constant():
    assert "png" in B.VALID_FORMATS
    assert "pdf" in B.VALID_FORMATS
    assert "gif" in B.VALID_FORMATS


# ── backend: capture with mocked screencapture ──────────────────────────────

def _mock_screencapture_success():
    """Returns a (mock_post, created_file_path) pair.

    The mock creates a 1-byte file at the destination so describe_capture
    can read its size.
    """
    def factory(args, **kwargs):
        cmd = args
        # Last arg is the output path
        out_path = Path(cmd[-1])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"\x89PNG_FAKE")
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m
    return factory


def test_capture_full_constructs_correct_flags(tmp_path):
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        # Last arg is output file
        Path(cmd[-1]).write_bytes(b"\x89PNG")
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m
    with patch("subprocess.run", side_effect=fake_run):
        cfg = B.load_config()
        meta = B.capture_full(output_path=str(tmp_path / "x.png"), format_="jpg", config=cfg)
    assert captured["cmd"][0] == "/usr/sbin/screencapture"
    assert "-t" in captured["cmd"]
    idx = captured["cmd"].index("-t")
    assert captured["cmd"][idx + 1] == "jpg"
    assert meta["format"] == "png"  # extension on file
    assert meta["source"] == "full"


def test_capture_full_includes_cursor_flag(tmp_path):
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        Path(cmd[-1]).write_bytes(b"\x89PNG")
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m
    with patch("subprocess.run", side_effect=fake_run):
        B.capture_full(output_path=str(tmp_path / "x.png"), include_cursor=True)
    assert "-C" in captured["cmd"]


def test_capture_region_uses_r_flag(tmp_path):
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        Path(cmd[-1]).write_bytes(b"\x89PNG")
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m
    with patch("subprocess.run", side_effect=fake_run):
        B.capture_region(x=10, y=20, width=300, height=400, output_path=str(tmp_path / "r.png"))
    assert "-R" in captured["cmd"]
    idx = captured["cmd"].index("-R")
    assert captured["cmd"][idx + 1] == "10,20,300,400"


def test_capture_window_uses_l_flag(tmp_path):
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        Path(cmd[-1]).write_bytes(b"\x89PNG")
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m
    with patch("subprocess.run", side_effect=fake_run):
        B.capture_window(window_id=12345, output_path=str(tmp_path / "w.png"))
    assert "-l" in captured["cmd"]
    idx = captured["cmd"].index("-l")
    assert captured["cmd"][idx + 1] == "12345"


def test_capture_full_propagates_failure(tmp_path):
    def fake_run(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 1
        m.stderr = "could not create image from display"
        return m
    with patch("subprocess.run", side_effect=fake_run):
        with pytest.raises(RuntimeError, match="could not create image"):
            B.capture_full(output_path=str(tmp_path / "x.png"))


# ── backend: convert ─────────────────────────────────────────────────────────

def test_convert_image_uses_sips(tmp_path):
    src = tmp_path / "in.png"
    src.write_bytes(b"\x89PNG_FAKE")
    captured = {}
    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        dst = Path(cmd[cmd.index("--out") + 1])
        dst.write_bytes(b"FAKE")
        m = MagicMock()
        m.returncode = 0
        return m
    with patch("shutil.which", return_value="/usr/bin/sips"):
        with patch("subprocess.run", side_effect=fake_run):
            result = B.convert_image(str(src), target_format="jpg")
    assert captured["cmd"][0] == "/usr/bin/sips"
    assert "jpg" in captured["cmd"]
    assert result["format"] == "jpg"


def test_convert_image_rejects_bad_format(tmp_path):
    src = tmp_path / "in.png"
    src.write_bytes(b"\x89PNG")
    with patch("shutil.which", return_value="/usr/bin/sips"):
        with pytest.raises(ValueError, match="Unsupported format"):
            B.convert_image(str(src), target_format="xyz")


# ── session ─────────────────────────────────────────────────────────────────

def test_session_record_and_load(tmp_path):
    session_file = tmp_path / "s.json"
    meta = {"path": "/tmp/a.png", "bytes": 100, "format": "png", "source": "full"}
    S.record_capture(meta, session_file=session_file)
    S.record_capture({**meta, "path": "/tmp/b.png", "bytes": 200}, session_file=session_file)
    hist = S.load_history(session_file=session_file)
    assert len(hist) == 2
    assert hist[0]["path"] == "/tmp/a.png"
    assert hist[1]["path"] == "/tmp/b.png"
    state = S.get_state()
    assert state["total_captures"] == 2
    assert state["total_bytes"] == 300


def test_session_clear_resets_everything(tmp_path):
    session_file = tmp_path / "s.json"
    S.record_capture({"path": "/tmp/a.png", "bytes": 100, "format": "png"}, session_file=session_file)
    S.clear_history(session_file=session_file)
    assert S.get_state()["total_captures"] == 0
    assert S.load_history(session_file=session_file) == []


# ── CLI: integration via CliRunner ──────────────────────────────────────────

def test_cli_help_shows_command_groups():
    runner = CliRunner()
    result = runner.invoke(C.cli, ["--help"])
    assert result.exit_code == 0
    assert "capture" in result.output
    assert "config" in result.output
    assert "session" in result.output


def test_cli_displays_json_output():
    runner = CliRunner()
    with patch.object(C, "list_displays", return_value=[{"index": 1, "name": "MockDisplay", "resolution": "1x1", "main": True}]):
        result = runner.invoke(C.cli, ["--json", "displays"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["name"] == "MockDisplay"


def test_cli_config_set_coerces_bool():
    runner = CliRunner()
    with runner.isolated_filesystem():
        cfg = Path("cfg.json")
        result = runner.invoke(C.cli, ["--config", str(cfg), "config", "set", "play_sounds", "false"])
        assert result.exit_code == 0
        # Now read it back
        result2 = runner.invoke(C.cli, ["--config", str(cfg), "--json", "config", "get", "play_sounds"])
        data = json.loads(result2.output)
        assert data["play_sounds"] is False


def test_cli_capture_full_reports_runtime_error():
    runner = CliRunner()
    with patch.object(C, "capture_full", side_effect=RuntimeError("screencapture failed (rc=1): could not create image from display")):
        result = runner.invoke(C.cli, ["capture", "full", "--output", "/tmp/x.png"])
    assert result.exit_code != 0
    assert "could not create image" in result.output


def test_cli_unknown_command_exits_nonzero():
    runner = CliRunner()
    result = runner.invoke(C.cli, ["nonexistent"])
    assert result.exit_code != 0
