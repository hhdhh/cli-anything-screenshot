# Screenshot CLI

A macOS screenshot CLI for scripts and AI agents. Capture images, convert formats, and inspect session history through commands with optional JSON output.

Built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology. This project wraps macOS system binaries; it does not implement cross-platform screen capture.

## Requirements

- macOS with `screencapture` and `sips` available.
- Python 3.10 or later.
- Screen Recording permission for the terminal or host application when required by macOS.

Linux and Windows can inspect the Python code, but cannot use the native capture backend as shipped.

## Install

```bash
git clone https://github.com/hhdhh/cli-anything-screenshot.git
cd cli-anything-screenshot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cli-anything-screenshot --help
```

## Capture and convert

```bash
cli-anything-screenshot capture full --no-sounds --output shot.png
cli-anything-screenshot capture region -x 0 -y 0 -w 800 -h 600
cli-anything-screenshot convert shot.png --format jpg
cli-anything-screenshot --json displays
```

Run `cli-anything-screenshot` without a subcommand to enter the interactive REPL.

## Command groups

| Group | Purpose |
| --- | --- |
| `capture` | Full-screen, region, and window capture |
| `convert` | Image format conversion through `sips` |
| `displays` | Display information |
| `windows` | Window-discovery command; enumeration is currently a placeholder |
| `config` | Read or update persistent settings |
| `session` | Inspect or clear capture history |

Window capture accepts an existing window ID. The current `windows` command does not provide a working window-enumeration implementation.

## Persistent state

- Configuration: `~/.cli-anything-screenshot/config.json`; override with `--config`.
- Capture history: `~/.cli-anything-screenshot/session.json`.

Screenshots can contain private information. Check the captured image before uploading it or sharing it with an agent.

## Tests and platform limits

```bash
python -m pytest tests/ -v
```

The tests use mocked capture and conversion commands, but some discovery assertions still assume macOS binaries. Run the suite on macOS. Mocked tests do not verify screen-recording permissions or real captured pixels.

The repository includes a macOS CI matrix. See [workflow runs](https://github.com/hhdhh/cli-anything-screenshot/actions) for the recorded status instead of relying on a hard-coded test count.

## Implementation

- `cli_anything/screenshot/screenshot_cli.py` — Click commands and REPL.
- `cli_anything/screenshot/core/session.py` — session state and capture history.
- `cli_anything/screenshot/utils/screencapture_backend.py` — native command wrappers.
- [SKILL.md](SKILL.md) — agent-facing usage.

## License

No repository license file is present at the reviewed revision. Confirm ownership and choose a license before describing the package as permissively licensed.
