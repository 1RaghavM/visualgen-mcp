"""Entry point: `python -m visualgen_mcp` or `uvx visualgen-mcp`."""

from __future__ import annotations

from dotenv import load_dotenv

from visualgen_mcp.server import run


def main() -> None:
    """Load `.env` if present, then start the server over stdio."""
    load_dotenv()
    run()


if __name__ == "__main__":
    main()
