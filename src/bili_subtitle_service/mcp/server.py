from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp

from bili_subtitle_service.mcp.tools import extract_subtitle_tool


def create_mcp_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8311,
    path: str = "/mcp",
) -> FastMCP:
    server = FastMCP(
        "bili-subtitle-service",
        instructions=(
            "Agent-facing tools for extracting cleaned Bilibili video subtitles. "
            "Use these tools when the user sends a Bilibili/B23 link and asks Alice "
            "to understand, summarize, or answer questions about the video."
        ),
        host=host,
        port=port,
        streamable_http_path=path,
        stateless_http=True,
        json_response=True,
    )
    _register_tools(server)
    return server


def create_mcp_http_app(
    *,
    host: str = "127.0.0.1",
    port: int = 8311,
    path: str = "/mcp",
) -> ASGIApp:
    return create_mcp_server(host=host, port=port, path=path).streamable_http_app()


def run_stdio_server() -> None:
    create_mcp_server().run("stdio")


def run_streamable_http_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8311,
    path: str = "/mcp",
) -> None:
    create_mcp_server(host=host, port=port, path=path).run("streamable-http")


def _register_tools(server: FastMCP) -> None:
    server.tool(
        name="extract_subtitle",
        description=(
            "Extract cleaned subtitle text from a Bilibili video URL or b23.tv short link. "
            "Returns video title, bvid, aid, cid, part title, selected subtitle metadata, "
            "and cleaned transcript text. Optional page selects a specific 分P."
        ),
    )(extract_subtitle_tool)
