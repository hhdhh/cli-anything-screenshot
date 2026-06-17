# Test Documentation — screenshot-harness

## Coverage

19 unit + integration tests covering the public surface of the harness.
No real screen capture is performed; the `screencapture` and `sips` binaries
are mocked.

## Groups

| Group | Tests | What it guards |
|------|-------|----------------|
| Discovery & config | 4 | `find_screencapture`, `load_config` defaults, round-trip persistence, `VALID_FORMATS` |
| Capture (mocked) | 5 | Flag construction for full / region / window, `-C` cursor toggle, runtime error propagation |
| Convert | 2 | `sips` invocation path, format validation |
| Session | 2 | Record + load history, `clear_history` resets state |
| CLI integration | 4 | `--help` shape, `--json` output, `config set` boolean coercion, error surfacing, unknown commands |

## Running

```bash
PYTHONPATH=. python3 -m pytest tests/ -v
```

All tests pass on macOS with Python 3.9. The harness itself requires 3.10+
at runtime for PEP 604 union syntax in the vendored REPL skin, but the
backend / session / CLI code is 3.9 compatible.

## Known limitations (intentional, not bugs)

- `screencapture` requires a real display server. CI / headless systems
  will see `could not create image from display` — the harness surfaces
  this verbatim rather than swallowing it.
- `list_windows` returns `[]` because macOS does not expose stable window
  IDs to shell tools without accessibility permissions.
