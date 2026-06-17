"""Test config: redirect pytest's tmp_path to /tmp so tests work under
sandboxed tmp dirs (e.g. /private/var/folders/...) that may be read-only.
Also pre-create the root so FileNotFoundError cannot occur.

Additionally: every test gets a writable, isolated DEFAULT_SESSION_FILE and
a clean in-memory session state, so e2e tests that drive the CLI through
Click don't trip over the user's real ~/.cli-anything-screenshot/ (which the
sandbox may block) or over a previous test's counters."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP_ROOT = "/tmp/cli-anything-screenshot-tests"
os.makedirs(_TMP_ROOT, exist_ok=True)


@pytest.fixture
def tmp_path():
    """Per-test tmp directory under /tmp, auto-cleaned."""
    d = tempfile.mkdtemp(prefix="t-", dir=_TMP_ROOT)
    try:
        yield Path(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(autouse=True)
def _isolate_session(tmp_path, monkeypatch):
    """Pin the session file under tmp_path and reset the in-memory state.

    - The CLI / session modules both import `DEFAULT_SESSION_FILE` from the
      backend at module-load time. We patch it on BOTH the backend and the
      re-exporting modules so any code path that holds the original ref
      still writes to a tmp file.
    - `_state` is a module-level dict in core/session.py and would otherwise
      leak counters across tests; reset_state() clears it.
    """
    from cli_anything.screenshot.utils import screencapture_backend as B
    from cli_anything.screenshot.core import session as S

    fake_session = tmp_path / "session.json"
    monkeypatch.setattr(B, "DEFAULT_SESSION_FILE", fake_session)
    monkeypatch.setattr(S, "DEFAULT_SESSION_FILE", fake_session)
    S.reset_state()
    yield
    S.reset_state()
