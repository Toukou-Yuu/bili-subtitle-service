from __future__ import annotations

import argparse
import asyncio
import json
import subprocess

import uvicorn

from bili_subtitle_service.extractor import extract_subtitle
from bili_subtitle_service.mcp.server import run_stdio_server, run_streamable_http_server


def main() -> None:
    parser = argparse.ArgumentParser(prog="bili-subtitle-service")
    subcommands = parser.add_subparsers(dest="command", required=True)

    serve_parser = subcommands.add_parser("serve", help="Start the REST API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", default=8310, type=int)

    extract_parser = subcommands.add_parser("extract", help="Extract a Bilibili subtitle once")
    extract_parser.add_argument("url")
    extract_parser.add_argument("--page", type=int, default=None)

    subcommands.add_parser("mcp", help="Start stdio MCP server")

    mcp_http_parser = subcommands.add_parser(
        "mcp-http",
        help="Start HTTP/Streamable HTTP MCP server",
    )
    mcp_http_parser.add_argument("--host", default="127.0.0.1")
    mcp_http_parser.add_argument("--port", default=8311, type=int)
    mcp_http_parser.add_argument("--path", default="/mcp")

    health_parser = subcommands.add_parser("healthcheck", help="Check REST API health endpoint")
    health_parser.add_argument("--port", default=8310, type=int)

    args = parser.parse_args()
    if args.command == "serve":
        uvicorn.run("bili_subtitle_service.app:app", host=args.host, port=args.port, reload=False)
    elif args.command == "extract":
        result = asyncio.run(extract_subtitle(args.url, page=args.page))
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    elif args.command == "mcp":
        run_stdio_server()
    elif args.command == "mcp-http":
        run_streamable_http_server(host=args.host, port=args.port, path=args.path)
    elif args.command == "healthcheck":
        subprocess.run(
            [
                "python",
                "-c",
                "import urllib.request; "
                f"urllib.request.urlopen('http://127.0.0.1:{args.port}/v1/health', timeout=3)",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
