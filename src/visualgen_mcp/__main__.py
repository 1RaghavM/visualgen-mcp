"""Entry point: `python -m visualgen_mcp`, `uvx visualgen-mcp`, or `... init`."""

from __future__ import annotations

import sys

from dotenv import load_dotenv


def main() -> None:
    """Dispatch on argv: `init` runs the wizard, everything else runs the server."""
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        from visualgen_mcp.wizard import run

        raise SystemExit(run())

    load_dotenv()
    from visualgen_mcp.server import run as run_server

    run_server()


if __name__ == "__main__":
    main()
