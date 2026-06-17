"""screencapture_backend.py - wraps macOS `screencapture` CLI.

Locates the screencapture binary, executes captures, and returns metadata.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


SCREENCAPTURE_BIN = "/usr/sbin/screencapture"

VALID_FORMATS = ("png", "pdf", "jpg", "tiff", "gif", "bmp", "pict")

DEFAULT_CONFIG_DIR = Path.home() / ".cli-anything-screenshot"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_SESSION_FILE = DEFAULT_CONFIG_DIR / "session.json"

DEFAULTS: Dict[str, Any] = {
    "output_dir": str(Path.home() / "Pictures" / "Screenshots"),
    "default_format": "png",
    "play_sounds": True,
    "include_cursor": False,
    "capture_shadow": True,
    "add_dpi_metadata": True,
}


def find_screencapture() -> str:
    """Return the screencapture binary path, raising if missing."""
    if not Path(SCREENCAPTURE_BIN).exists():
        resolved = shutil.which("screencapture")
        if resolved:
            return resolved
        raise RuntimeError(
            f"screencapture not found at {SCREENCAPTURE_BIN} "
            "and not on PATH. This harness only works on macOS."
        )
    return SCREENCAPTURE_BIN


def _run_screencapture(args, timeout=60.0):
    """Execute screencapture, capture stderr, raise on non-zero exit."""
    bin_path = find_screencapture()
    cmd = [bin_path] + list(args)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"screencapture timed out after {timeout}s") from e
    if proc.returncode != 0:
        raise RuntimeError(
            f"screencapture failed (rc={proc.returncode}): {proc.stderr.strip()}"
        )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}


def load_config(config_file=None):
    """Load configuration, falling back to DEFAULTS if missing."""
    path = Path(config_file) if config_file else DEFAULT_CONFIG_FILE
    if not path.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_config(config, config_file=None):
    """Persist configuration to disk."""
    path = Path(config_file) if config_file else DEFAULT_CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2))


def ensure_output_dir(output_dir):
    """Make sure the output directory exists."""
    p = Path(output_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _timestamped_path(output_dir, format_):
    return output_dir / ("screen_" + time.strftime("%Y%m%d_%H%M%S") + "." + format_)


def capture_full(
    output_path=None,
    display=None,
    include_cursor=False,
    play_sounds=True,
    format_="png",
    config=None,
):
    """Capture the entire screen (or a specific display)."""
    cfg = config or load_config()
    if output_path:
        out_file = Path(output_path).expanduser()
        out_dir = ensure_output_dir(str(out_file.parent))
    else:
        out_dir = ensure_output_dir(cfg["output_dir"])
        out_file = _timestamped_path(out_dir, format_)

    args = []
    if not play_sounds:
        args.append("-x")
    if include_cursor:
        args.append("-C")
    if display is not None:
        args.append("-D" + str(display))
    args.extend(["-t", format_])
    args.append(str(out_file))

    _run_screencapture(args)
    return _describe_capture(out_file, source="full", display=display)


def capture_window(
    window_id,
    output_path=None,
    capture_shadow=True,
    include_attached=True,
    play_sounds=True,
    format_="png",
    config=None,
):
    """Capture a specific window by its ID."""
    cfg = config or load_config()
    if output_path:
        out_file = Path(output_path).expanduser()
        out_dir = ensure_output_dir(str(out_file.parent))
    else:
        out_dir = ensure_output_dir(cfg["output_dir"])
        out_file = _timestamped_path(out_dir, format_)

    args = []
    if not play_sounds:
        args.append("-x")
    if not capture_shadow:
        args.append("-o")
    if not include_attached:
        args.append("-a")
    args.extend(["-l", str(window_id)])
    args.extend(["-t", format_])
    args.append(str(out_file))

    _run_screencapture(args)
    return _describe_capture(out_file, source="window", window_id=window_id)


def capture_region(
    x, y, width, height,
    output_path=None,
    play_sounds=True,
    format_="png",
    config=None,
):
    """Capture a rectangular region of the screen."""
    cfg = config or load_config()
    if output_path:
        out_file = Path(output_path).expanduser()
        out_dir = ensure_output_dir(str(out_file.parent))
    else:
        out_dir = ensure_output_dir(cfg["output_dir"])
        out_file = _timestamped_path(out_dir, format_)

    args = []
    if not play_sounds:
        args.append("-x")
    args.extend(["-R", "{0},{1},{2},{3}".format(x, y, width, height)])
    args.extend(["-t", format_])
    args.append(str(out_file))

    _run_screencapture(args)
    return _describe_capture(out_file, source="region", region={"x": x, "y": y, "w": width, "h": height})


def list_displays():
    """List connected displays using system_profiler (best-effort)."""
    try:
        proc = subprocess.run(
            ["system_profiler", "-json", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=10, check=False
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            displays = data.get("SPDisplaysDataType", [])
            result = []
            for i, d in enumerate(displays, start=1):
                result.append({
                    "index": i,
                    "name": d.get("_name", "Unknown"),
                    "resolution": d.get("spdisplays_resolution", "Unknown"),
                    "main": d.get("spdisplays_main", False),
                })
            return result
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return [{"index": 1, "name": "Main Display", "resolution": "unknown", "main": True}]


def list_windows():
    """List currently visible windows with IDs (best-effort, requires AppleScript).

    Returns an empty list with a documented limitation: macOS does not expose
    stable window IDs to shell tools without accessibility permissions.
    """
    return []


def convert_image(input_path, output_path=None, target_format="png"):
    """Convert an image between formats using macOS `sips`."""
    sips = shutil.which("sips")
    if not sips:
        raise RuntimeError("`sips` not found; this backend requires macOS.")
    src = Path(input_path).expanduser()
    if not src.exists():
        raise FileNotFoundError("Input not found: " + str(src))
    if target_format not in VALID_FORMATS:
        raise ValueError("Unsupported format: " + target_format + ". Valid: " + str(VALID_FORMATS))

    dst = Path(output_path).expanduser() if output_path else src.with_suffix("." + target_format)
    proc = subprocess.run(
        [sips, "-s", "format", target_format, str(src), "--out", str(dst)],
        capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError("sips failed: " + proc.stderr.strip())
    return {"input": str(src), "output": str(dst), "format": target_format}


def _describe_capture(path, **extra):
    """Build a metadata dict for a freshly captured file."""
    stat = path.stat() if path.exists() else None
    return {
        "path": str(path),
        "format": path.suffix.lstrip("."),
        "bytes": stat.st_size if stat else 0,
        "mtime": stat.st_mtime if stat else 0,
        **extra,
    }
