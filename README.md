# screenshot-harness

A CLI for the macOS Screenshot.app GUI, built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology.

## Install

```bash
pip install -e .
```

## Usage

```bash
# subcommand mode
cli-anything-screenshot capture full --no-sounds --output shot.png
cli-anything-screenshot capture region -x 0 -y 0 -w 1920 -h 1080
cli-anything-screenshot convert shot.png --format jpg

# interactive
cli-anything-screenshot
```

See [SKILL.md](./SKILL.md) for the agent-facing description.
