# bili-subtitle-service

Bilibili subtitle extraction service and MCP adapter for Hermes/Alice.

## What it does

- `GET /extract?url=...` extracts the selected Bilibili subtitle.
- `POST /notes/from-url` extracts a subtitle and persists a Markdown video note.
- `GET /notes/{document_id}` reads a saved Markdown note.
- Supports normal Bilibili video URLs, watch-later URLs with `bvid=...`, and `b23.tv` mobile short links.
- Returns structured metadata: title, bvid, aid, cid, 分P title, selected subtitle language, and cleaned transcript text.
- Exposes an HTTP/Streamable MCP server so Alice can call the extractor from Discord/Telegram/CLI.

## Runtime config

Runtime config is intentionally injected by file/env instead of being baked into the image.

```bash
export BILI_SUBTITLE_CONFIG_FILE=/config/service.yaml
```

Example config:

```yaml
fetch:
  timeout_seconds: 15
  user_agent: "Mozilla/5.0 (compatible; bili-subtitle-service/0.1)"
  proxy: null
  cookie_file: null

summary:
  model: deepseek-v4-flash
  reasoning_effort: high

storage:
  enabled: true
  library_dir: /data/library

retrieval:
  enabled: false
  base_url: http://retrieval-api:8000/v1
  collection: bili_video_notes
  sync_by_default: false
```

`summary` is reserved for downstream Alice/Hermes summary flows. Subtitle extraction itself is deterministic and does not call an LLM.

Markdown notes are the persistent source of truth. Retrieval/Qdrant is an optional semantic index derived from those Markdown files.

Environment variables override the config file:

- `BILI_SUBTITLE_TIMEOUT_SECONDS`
- `BILI_SUBTITLE_USER_AGENT`
- `BILI_SUBTITLE_PROXY`
- `BILI_SUBTITLE_COOKIE_FILE` or `BILI_SUBTITLE_COOKIE` for videos whose subtitle list is only visible in a logged-in Bilibili browser session. Values may be a full Cookie header or only the raw `SESSDATA` value; bare values are normalized to `SESSDATA=...`.
- `BILI_SUBTITLE_SUMMARY_MODEL`
- `BILI_SUBTITLE_SUMMARY_REASONING_EFFORT`
- `BILI_SUBTITLE_STORAGE_ENABLED`
- `BILI_SUBTITLE_LIBRARY_DIR`
- `BILI_SUBTITLE_RETRIEVAL_ENABLED`
- `BILI_SUBTITLE_RETRIEVAL_BASE_URL`
- `BILI_SUBTITLE_RETRIEVAL_COLLECTION`
- `BILI_SUBTITLE_RETRIEVAL_SYNC_BY_DEFAULT`
- `BILI_SUBTITLE_LOG_LEVEL`

## Markdown persistence and retrieval

Save a note with transcript, AI analysis, categories, profile signals, and metadata:

```bash
curl -X POST http://127.0.0.1:8310/notes/from-url \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://b23.tv/snbsbAC",
    "analysis": "Alice generated explanation goes here.",
    "categories": ["哲学", "资本主义批判"],
    "tags": ["个性化", "人形洞"],
    "profile_signals": ["关注市场如何塑造欲望"],
    "sync_retrieval": true
  }'
```

Saved files use this shape:

```text
/data/library/YYYY/MM/bili_<BVID>_p<PAGE>.md
```

The Markdown file contains YAML frontmatter plus sections for metadata, AI 讲解分析, 分类与画像信号, and 字幕正文. Temporary subtitle URLs and cookies are not persisted.

When retrieval is enabled, the full Markdown note is upserted into the configured collection, usually `bili_video_notes`, with metadata marking it as `doc_type=bili_video_note` and `source_type=mixed_transcript_and_ai_analysis`. This lets future Alice queries retrieve both the structured AI explanation and original transcript evidence while keeping Markdown as the rebuildable source.

## Run locally

```bash
uv sync
cp config/service.example.yaml /tmp/bili-subtitle-service.yaml
BILI_SUBTITLE_CONFIG_FILE=/tmp/bili-subtitle-service.yaml \
  uv run bili-subtitle-service serve --host 0.0.0.0 --port 8310
```

Extract once:

```bash
BILI_SUBTITLE_CONFIG_FILE=config/service.example.yaml \
  uv run bili-subtitle-service extract 'https://www.bilibili.com/video/BV...'
```

HTTP:

```bash
curl 'http://127.0.0.1:8310/extract?url=https%3A%2F%2Fwww.bilibili.com%2Fvideo%2FBV...'
```

MCP HTTP server:

```bash
BILI_SUBTITLE_CONFIG_FILE=config/service.example.yaml \
  uv run bili-subtitle-service mcp-http --host 0.0.0.0 --port 8311 --path /mcp
```

Hermes config:

```yaml
mcp_servers:
  bili_subtitle:
    url: http://127.0.0.1:8311/mcp
    enabled: true
    timeout: 120
    connect_timeout: 60
```

## Docker

```bash
docker build -t bili-subtitle-service:latest .
docker compose -f docker-compose.prod.yml up -d
```

Published images are pushed to Docker Hub by GitHub Actions using the configured `secrets.dockerhubname` namespace. The workflow does not publish to GHCR.
