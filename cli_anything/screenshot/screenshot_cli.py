"""screenshot_cli.py - main Click entry point for the screenshot harness.

A CLI for the macOS Screenshot.app GUI, powered by the `screencapture` backend.
Exposes a subcommand tree plus an interactive REPL.

Usage:
    # one-shot
    python -m cli_anything.screenshot.screenshot_cli capture full
    python -m cli_anything.screenshot.screenshot_cli capture region -x 100 -y 100 -w 800 -h 600
    python -m cli_anything.screenshot.screenshot_cli config get

    # interactive
    python -m cli_anything.screenshot.screenshot_cli
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

from cli_anything.screenshot.utils.screencapture_backend import (
    DEFAULTS,
    VALID_FORMATS,
    capture_full,
    capture_region,
    capture_window,
    convert_image,
    list_displays,
    list_windows,
    load_config,
    save_config,
)
from cli_anything.screenshot.core.session import (
    clear_history,
    get_state,
    load_history,
    record_capture,
)


_json_mode = False


def output(data: Any, message: str = "") -> None:
    if _json_mode:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.secho(message, fg="green")
        if isinstance(data, dict):
            for k, v in data.items():
                click.echo(f"  {k}: {v}")
        elif isinstance(data, list):
            for item in data:
                click.echo(f"  - {item}")
        else:
            click.echo(f"  {data}")


def handle_error(func):
    """Decorator: catch RuntimeError/FileNotFoundError/ValueError, print nicely."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            click.secho("Error: " + str(e), fg="red", err=True)
            sys.exit(1)
    wrapper.__name__ = func.__name__
    return wrapper


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--config", "config_file", type=click.Path(), default=None, help="Config file path")
@click.pass_context
def cli(ctx, use_json, config_file):
    """CLI for the macOS Screenshot GUI - powered by screencapture."""
    global _json_mode
    _json_mode = use_json
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ── capture ──────────────────────────────────────────────────────────────────

@cli.group()
def capture():
    """Capture screenshots."""


@capture.command("full")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--display", "-D", type=int, default=None)
@click.option("--cursor/--no-cursor", default=None)
@click.option("--sounds/--no-sounds", default=None)
@click.option("--format", "format_", type=click.Choice(VALID_FORMATS), default=None)
@click.pass_context
@handle_error
def capture_full_cmd(ctx, output, display, cursor, sounds, format_):
    """Capture the full screen (or a specific display)."""
    cfg = load_config(ctx.obj.get("config_file"))
    fmt = format_ or cfg["default_format"]
    cur = cursor if cursor is not None else cfg["include_cursor"]
    snd = sounds if sounds is not None else cfg["play_sounds"]
    meta = capture_full(
        output_path=output,
        display=display,
        include_cursor=cur,
        play_sounds=snd,
        format_=fmt,
        config=cfg,
    )
    record_capture(meta)
    output(meta, "Captured full screen")


@capture.command("region")
@click.option("-x", "x", type=int, required=True)
@click.option("-y", "y", type=int, required=True)
@click.option("-w", "width", type=int, required=True)
@click.option("-h", "height", type=int, required=True)
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--sounds/--no-sounds", default=None)
@click.option("--format", "format_", type=click.Choice(VALID_FORMATS), default=None)
@click.pass_context
@handle_error
def capture_region_cmd(ctx, x, y, width, height, output, sounds, format_):
    """Capture a rectangular region."""
    cfg = load_config(ctx.obj.get("config_file"))
    meta = capture_region(
        x=x, y=y, width=width, height=height,
        output_path=output,
        play_sounds=(sounds if sounds is not None else cfg["play_sounds"]),
        format_=(format_ or cfg["default_format"]),
        config=cfg,
    )
    record_capture(meta)
    output(meta, "Captured region")


@capture.command("window")
@click.option("--id", "window_id", type=int, required=True, help="Window ID (use a system tool to find it)")
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--shadow/--no-shadow", default=None)
@click.option("--sounds/--no-sounds", default=None)
@click.option("--format", "format_", type=click.Choice(VALID_FORMATS), default=None)
@click.pass_context
@handle_error
def capture_window_cmd(ctx, window_id, output, shadow, sounds, format_):
    """Capture a specific window by ID."""
    cfg = load_config(ctx.obj.get("config_file"))
    meta = capture_window(
        window_id=window_id,
        output_path=output,
        capture_shadow=(shadow if shadow is not None else cfg["capture_shadow"]),
        play_sounds=(sounds if sounds is not None else cfg["play_sounds"]),
        format_=(format_ or cfg["default_format"]),
        config=cfg,
    )
    record_capture(meta)
    output(meta, "Captured window")


# ── displays / windows ──────────────────────────────────────────────────────

@cli.command("displays")
@click.pass_context
@handle_error
def displays_cmd(ctx):
    """List connected displays."""
    result = list_displays()
    output(result, f"{len(result)} display(s) found")


@cli.command("windows")
@click.pass_context
@handle_error
def windows_cmd(ctx):
    """List currently visible windows (best-effort)."""
    result = list_windows()
    if not result:
        output(
            {"note": "Window enumeration requires accessibility permissions; not available from shell."},
            "0 windows (see docs)"
        )
    else:
        output(result, f"{len(result)} window(s) found")


# ── convert ─────────────────────────────────────────────────────────────────

@cli.command("convert")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None)
@click.option("--format", "target_format", type=click.Choice(VALID_FORMATS), required=True)
@handle_error
def convert_cmd(input_path, output, target_format):
    """Convert a screenshot to a different format."""
    result = convert_image(input_path, output, target_format)
    output(result, f"Converted to {target_format}")


# ── config ──────────────────────────────────────────────────────────────────

@cli.group()
def config():
    """Configuration management."""


@config.command("get")
@click.argument("key", required=False)
@click.pass_context
@handle_error
def config_get(ctx, key):
    """Show a config value (or all)."""
    cfg = load_config(ctx.obj.get("config_file"))
    if key:
        if key not in cfg:
            click.secho("Unknown key: " + key, fg="red", err=True)
            sys.exit(1)
        output({key: cfg[key]}, f"{key} = {cfg[key]}")
    else:
        output(cfg, "Current config")


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
@handle_error
def config_set(ctx, key, value):
    """Set a config value (booleans auto-coerced)."""
    if key not in DEFAULTS:
        click.secho("Unknown key: " + key + ". Valid: " + ", ".join(DEFAULTS.keys()), fg="red", err=True)
        sys.exit(1)
    cfg = load_config(ctx.obj.get("config_file"))
    if isinstance(DEFAULTS[key], bool):
        value = value.lower() in ("1", "true", "yes", "on")
    elif isinstance(DEFAULTS[key], int):
        value = int(value)
    cfg[key] = value
    save_config(cfg, ctx.obj.get("config_file"))
    output({key: cfg[key]}, f"Set {key} = {cfg[key]}")


@config.command("path")
@click.pass_context
@handle_error
def config_path(ctx):
    """Show the config file path."""
    from cli_anything.screenshot.utils.screencapture_backend import DEFAULT_CONFIG_FILE
    output({"path": str(DEFAULT_CONFIG_FILE)}, DEFAULT_CONFIG_FILE)


# ── session ─────────────────────────────────────────────────────────────────

@cli.group()
def session():
    """Session management."""


@session.command("status")
@click.pass_context
@handle_error
def session_status(ctx):
    """Show in-memory session state."""
    state = get_state()
    output(state, "Session state")


@session.command("history")
@click.option("--limit", "-n", type=int, default=20)
@click.pass_context
@handle_error
def session_history(ctx, limit):
    """Show recent captures (max 20)."""
    hist = load_history()[-limit:]
    output(hist, f"{len(hist)} recent capture(s)")


@session.command("clear")
@handle_error
def session_clear():
    """Clear session history."""
    clear_history()
    output({"cleared": True}, "Session cleared")


# ── repl ────────────────────────────────────────────────────────────────────

@click.command(name="repl", hidden=True)
@click.pass_context
def repl(ctx):
    """Interactive REPL."""
    try:
        from cli_anything.screenshot.utils.repl_skin import ReplSkin
    except ImportError:
        ReplSkin = None

    if ReplSkin is None:
        click.echo("REPL skin unavailable; falling back to simple prompt.")
        _simple_repl()
        return

    skin = ReplSkin("screenshot", version="0.1.0", history_file="/private/tmp/test-codex/.screenshot-history")
    skin.print_banner()
    pt_session = skin.create_prompt_session()

    while True:
        try:
            line = skin.get_input(pt_session, project_name="screenshot")
        except (EOFError, KeyboardInterrupt):
            click.echo()
            skin.print_goodbye()
            break
        if not line:
            continue
        parts = line.split()
        cmd, args = parts[0], parts[1:]
        if cmd in ("quit", "exit"):
            skin.print_goodbye()
            break
        if cmd == "help":
            skin.help({c: c.get_short_help_str() if hasattr(c, "get_short_help_str") else "" for c in _repl_commands()})
            continue
        # Re-invoke via the click group
        sys.argv = ["screenshot"] + ([_json_arg()] if _json_mode else []) + [cmd] + args
        try:
            cli(standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            skin.error(str(e))


def _simple_repl():
    while True:
        try:
            line = input("screenshot> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("quit", "exit"):
            break
        parts = line.split()
        sys.argv = ["screenshot"] + ([_json_arg()] if _json_mode else []) + parts
        try:
            cli(standalone_mode=False)
        except SystemExit:
            pass


def _json_arg() -> str:
    return "--json"


def _repl_commands():
    """Return a name->cmd dict for help text (best-effort)."""
    return {
        "capture full": "Capture full screen",
        "capture region": "Capture region (needs -x -y -w -h)",
        "capture window": "Capture window by id",
        "displays": "List displays",
        "convert": "Convert format (sips)",
        "config get/set/path": "Configuration",
        "session status/history/clear": "Session",
        "quit": "Exit",
    }


def main():
    cli()


if __name__ == "__main__":
    main()
