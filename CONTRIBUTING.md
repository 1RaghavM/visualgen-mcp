# Contributing

Thanks for wanting to help. This is a small project. Keep changes small too.

## Dev environment

You need [uv](https://docs.astral.sh/uv/). Then:

```bash
git clone https://github.com/raghavmehta/visualgen-mcp.git
cd visualgen-mcp
uv sync --dev
```

Run the test suite:

```bash
uv run pytest
```

Run lint and type checks:

```bash
uv run ruff check
uv run ruff format --check
uv run mypy src/
```

All four must pass before you open a PR. CI runs the same checks.

Unit tests mock the google-genai client and never make real API calls. Integration tests under `tests/integration/` do hit the real API and are not run in CI — see `tests/integration/README.md` for how to run them manually.

## Adding a new provider

Providers live in `src/visualgen_mcp/providers/`. Each is a flat module that takes an already-constructed client as a parameter, so it's easy to mock. Copy the shape of `imagen.py` if you're adding a new image model; copy `veo.py` if you're adding something with an async submit/poll/download lifecycle.

Wire the new provider into `server.py` as a new `@mcp.tool()`-decorated function. Docstrings become tool descriptions — write them for Claude to read.

## Opening a PR

- One focused change per PR. Feature plus unrelated refactor = two PRs.
- Update the README tool reference if you change a public tool signature.
- Update the pricing dict in `server.py` if you add a new model.
- Include tests. If you can't mock something cleanly, the design is wrong — refactor until the mock is small.

## Code style

- Ruff (`uv run ruff check && uv run ruff format`). 100-char lines.
- `mypy --strict src/` must pass.
- Type hints on every function signature.
- No emojis anywhere — code, comments, docstrings, commit messages, or PR descriptions.
- Never `print()` to stdout in server code. Stdio mode uses stdout for JSON-RPC framing; writes corrupt it. Use `sys.stderr` or the `logging` module.
