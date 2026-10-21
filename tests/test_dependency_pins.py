"""Guard the mcp major-version bound.

``server.py`` imports ``mcp.server.fastmcp``, a module that exists only in the
v1 SDK. In v2 ``FastMCP`` was renamed to ``MCPServer`` and that module was
removed, so an unbounded ``mcp`` requirement lets a fresh install resolve v2 and
die on import before the stdio handshake. Clients report nothing but a closed
connection, which reads as a config or credential problem. Assert the bound
here, where the failure names its own cause.
"""

from __future__ import annotations

from importlib.metadata import version


def test_mcp_major_version_is_v1() -> None:
    installed = version("mcp")
    major = int(installed.split(".")[0])
    assert major == 1, (
        f"mcp {installed} is installed, but server.py imports "
        "mcp.server.fastmcp, which v2 removed. Keep the '<2' bound in "
        "pyproject.toml, or migrate the server to the v2 MCPServer API."
    )
