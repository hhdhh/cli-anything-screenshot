"""session.py - per-process state and persistent capture history.

Two layers:
- In-memory `_state` is the live context (last capture, counters).
- `session.json` on disk keeps a bounded history of recent captures.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from cli_anything.screenshot.utils.screencapture_backend import (
    DEFAULT_SESSION_FILE,
    load_config,
)


HISTORY_LIMIT = 20
_state: Dict[str, Any] = {
    "last_capture": None,
    "total_captures": 0,
    "total_bytes": 0,
}


def get_state() -> Dict[str, Any]:
    return dict(_state)


def reset_state() -> None:
    _state["last_capture"] = None
    _state["total_captures"] = 0
    _state["total_bytes"] = 0


def record_capture(meta: Dict[str, Any], session_file: Optional[Path] = None) -> None:
    """Update in-memory state and append to persistent history."""
    _state["last_capture"] = meta
    _state["total_captures"] += 1
    _state["total_bytes"] += meta.get("bytes", 0)

    path = Path(session_file) if session_file else DEFAULT_SESSION_FILE
    history = load_history(session_file=path)
    history.append(meta)
    history = history[-HISTORY_LIMIT:]
    _locked_save_json(path, {"history": history, "state": _state})


def load_history(session_file: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = Path(session_file) if session_file else DEFAULT_SESSION_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get("history", [])
    except (json.JSONDecodeError, OSError):
        return []


def clear_history(session_file: Optional[Path] = None) -> None:
    path = Path(session_file) if session_file else DEFAULT_SESSION_FILE
    if path.exists():
        path.unlink()
    reset_state()


def _locked_save_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomic JSON write to avoid corrupting session on concurrent saves.

    Uses the write-temp-then-rename pattern (atomic on POSIX) plus fsync.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".session-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
