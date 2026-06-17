---
name: cli-anything-screenshot
description: Use when the user wants to script, batch, or agent-drive the macOS Screenshot GUI. Wraps `screencapture` and `sips` behind a stateful subcommand CLI with JSON output, persistent config, and an interactive REPL.
---

# cli-anything-screenshot

A CLI harness for the macOS **Screenshot.app** GUI, built with the CLI-Anything methodology.

## What it does

Turns the macOS Screenshot GUI into a scriptable interface:

- **Subcommand CLI** — `capture full`, `capture region`, `capture window`, `convert`, `displays`, `windows`, `config`, `session`
- **Interactive REPL** — fall back to a unified prompt with history (uses `prompt_toolkit` if available)
- **JSON output** — every command works with `--json` for agent consumption
- **Persistent state** — captures are logged to `~/.cli-anything-screenshot/session.json` (last 20)
- **Type-safe config** — `config get/set/path` with boolean auto-coercion
- **Backend isolation** — `utils/screencapture_backend.py` wraps the `screencapture` and `sips` binaries, so the rest of the code is testable without a real display

## Quick start

```bash
# Discover displays
python -m cli_anything.screenshot.screenshot_cli --json displays

# Capture the full screen
python -m cli_anything.screenshot.screenshot_cli capture full --no-sounds --output shot.png

# Capture a region
python -m cli_anything.screenshot.screenshot_cli capture region -x 100 -y 100 -w 800 -h 600

# Convert PNG -> JPG
python -m cli_anything.screenshot.screenshot_cli convert shot.png --format jpg

# Interactive
python -m cli_anything.screenshot.screenshot_cli
```

## File layout

```
screenshot-harness/
  cli_anything/screenshot/
    screenshot_cli.py            # Click entry point + REPL
    core/session.py              # in-memory state + bounded history
    utils/screencapture_backend.py  # wraps `screencapture` and `sips`
    utils/repl_skin.py           # vendored from cli-anything-plugin
  tests/
    test_harness.py              # 19 tests, fully mocked
    TEST.md                      # this doc
  SKILL.md                       # you are here
  README.md
  setup.py
```

## Testing

`PYTHONPATH=. python3 -m pytest tests/ -v` — 19 passed, no real display required.

## Limitations

- macOS only (uses `/usr/sbin/screencapture` and `sips`)
- Real capture needs a window server
- `windows` command returns `[]` without accessibility permissions
