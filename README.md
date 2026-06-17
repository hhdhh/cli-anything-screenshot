# screenshot-harness

A CLI for the macOS Screenshot.app GUI, built with the
[CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology.

Wraps the `screencapture` and `sips` binaries behind a stateful subcommand
CLI with JSON output, a persistent config, an in-memory + on-disk capture
history, and an interactive REPL. Designed to be driven by humans, shell
scripts, and agents.

## Install

```bash
pip install -e .
# or, with the dev extras (pytest)
pip install -e ".[dev]"
```

## Usage

```bash
# subcommand mode
cli-anything-screenshot capture full --no-sounds --output shot.png
cli-anything-screenshot capture region -x 0 -y 0 -w 1920 -h 1080
cli-anything-screenshot convert shot.png --format jpg

# JSON output for agents
cli-anything-screenshot --json displays

# interactive REPL
cli-anything-screenshot
```

## Command groups

| Group      | What it does                                                |
|------------|-------------------------------------------------------------|
| `capture`  | `full` / `region` / `window` screenshotting                 |
| `convert`  | Format conversion via `sips` (png, jpg, pdf, gif, …)        |
| `displays` | List connected displays (JSON-friendly)                     |
| `windows`  | List on-screen windows (needs accessibility permission)     |
| `config`   | Persistent config: `get` / `set` / `path`                    |
| `session`  | Capture history: `status` / `history` / `clear`             |

## Testing

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
# 28 passed, 0 failed
```

The suite is fully mocked — no real screen capture, no real `sips`. It
covers the backend (`screencapture_backend.py`), the session module
(`core/session.py`), the Click group, and 9 end-to-end smoke tests that
exercise the full CLI entry point via `click.testing.CliRunner`.

CI runs the same suite on macOS for Python 3.10, 3.11, 3.12.

## File layout

```
screenshot-harness/
  cli_anything/screenshot/
    screenshot_cli.py            # Click entry point + REPL
    core/session.py              # in-memory state + bounded history
    utils/screencapture_backend.py  # wraps `screencapture` and `sips`
    utils/repl_skin.py           # vendored from cli-anything-plugin
  tests/
    conftest.py                  # autouse: tmp_path + session isolation
    test_harness.py              # 19 backend / session / CLI unit tests
    test_e2e_smoke.py            # 9 e2e tests via CliRunner
  SKILL.md                       # agent-facing description
  README.md                      # you are here
  setup.py
```

## Persistent state

- **Config:** `~/.cli-anything-screenshot/config.json` (override with `--config`)
- **Session history:** `~/.cli-anything-screenshot/session.json` (last 20 captures)

## See also

- [SKILL.md](./SKILL.md) — the agent-facing description (this CLI is shipped
  as a Codex skill under the same name).
