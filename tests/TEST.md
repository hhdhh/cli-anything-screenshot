# Test Documentation — screenshot-harness

## Coverage

28 tests covering the public surface of the harness. No real screen
capture is performed; the `screencapture` and `sips` binaries are
mocked, and the Click group is exercised end-to-end via
`click.testing.CliRunner`.

## Groups

| Group | Tests | What it guards |
|------|-------|----------------|
| Discovery & config | 4 | `find_screencapture`, `load_config` defaults, round-trip persistence, `VALID_FORMATS` |
| Capture (mocked) | 5 | Flag construction for full / region / window, `-C` cursor toggle, runtime error propagation |
| Convert | 2 | `sips` invocation path, format validation |
| Session | 2 | Record + load history, `clear_history` resets state |
| CLI integration | 4 | `--help` shape, `--json` output, `config set` boolean coercion, error surfacing, unknown commands |
| End-to-end smoke | 9 | Full Click group via `CliRunner`: capture writes a file, region emits JSON, session appends, convert uses sips, config round-trip, help shape, fallback for headless `displays` |
| **Total** | **28** | |

## Running

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
# 28 passed in ~0.1s
```

The `tests/conftest.py` autouse fixture pins `DEFAULT_SESSION_FILE` to
a per-test tmp path and calls `session.reset_state()` between tests,
so the CLI never tries to write under the user's real
`~/.cli-anything-screenshot/` and counters do not leak between tests.

CI runs the suite on macOS for Python 3.10 / 3.11 / 3.12. Local runs
on Python 3.9 also pass.

## Known limitations (intentional, not bugs)

- `screencapture` requires a real display server. CI / headless systems
  will see `could not create image from display` — the harness surfaces
  this verbatim rather than swallowing it.
- `list_windows` returns `[]` because macOS does not expose stable window
  IDs to shell tools without accessibility permissions.
