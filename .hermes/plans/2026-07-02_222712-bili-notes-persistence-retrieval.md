# Bilibili Video Notes Persistence + Retrieval Implementation Plan

> **For Hermes:** Implement directly with strict TDD where practical; each behavior gets tests before production code.

**Goal:** Add Markdown-first persistence for Bilibili subtitles, Alice/AI analysis, categories/profile signals, metadata, and optional retrieval-api indexing.

**Architecture:** Keep subtitle extraction deterministic. Add a notes/archive layer that saves human-readable Markdown as the source of truth under `/data/library`, then derives retrieval documents from that Markdown. Alice/Hermes supplies AI analysis/categories/profile signals through HTTP/MCP; the service stores and indexes them but does not call an LLM itself.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, httpx, Markdown files with YAML frontmatter, retrieval-api `/v1/collections` + `/v1/documents/upsert`.

---

## Decisions

1. Markdown files are the authoritative persistent asset.
2. Retrieval/Qdrant is an index, not the source of truth.
3. AI analysis should be indexed, but labeled as `source_type=ai_generated` and kept separate from transcript chunks via Markdown sections/metadata.
4. Transcript should also be indexed as evidence (`section_type=transcript`) so future answers can distinguish source text from interpretation.
5. Categories/profile signals are both Markdown content and metadata.
6. Cookies/auth URLs are never persisted.

## Tasks

### Task 1: Add config and models

Files:
- Modify `src/bili_subtitle_service/config.py`
- Modify `src/bili_subtitle_service/models.py`
- Test `tests/test_config.py`

Add storage config:
- `storage.enabled`
- `storage.library_dir`
- `retrieval.enabled`
- `retrieval.base_url`
- `retrieval.collection`
- `retrieval.sync_by_default`

Add request/response models for saving notes.

### Task 2: Markdown archive layer

Files:
- Create `src/bili_subtitle_service/notes.py`
- Test `tests/test_notes.py`

Implement:
- deterministic document id: `bili_<bvid>_p<page>`
- path: `<library_dir>/<YYYY>/<MM>/<document_id>.md`
- YAML frontmatter with video metadata, categories, tags, profile signals, analysis model, capture time
- sections: Metadata, AI 讲解分析, 分类与画像信号, 字幕正文
- safe read-back function for existing notes

### Task 3: Retrieval integration

Files:
- Create `src/bili_subtitle_service/retrieval.py`
- Test `tests/test_retrieval.py`

Implement:
- ensure collection exists with `markdown_semantic`
- upsert one Markdown document into retrieval-api
- metadata includes `source=bilibili`, `doc_type=bili_video_note`, `bvid`, `cid`, `categories`, `tags`, `profile_signals`, `contains_ai_analysis=true`

### Task 4: HTTP API

Files:
- Modify `src/bili_subtitle_service/app.py`
- Test `tests/test_api.py`

Add:
- `POST /notes/from-url`
- `GET /notes/{document_id}`

`POST /notes/from-url` extracts subtitle, writes Markdown, optionally syncs retrieval.

### Task 5: MCP tools

Files:
- Modify `src/bili_subtitle_service/mcp/tools.py`
- Modify `src/bili_subtitle_service/mcp/server.py`
- Test `tests/mcp/test_http_server.py` if needed

Add MCP tools:
- `save_video_note`
- `get_video_note`

### Task 6: Config, Docker, docs, deploy

Files:
- Modify `config/service.example.yaml`
- Modify `.env.example`
- Modify `docker-compose.prod.yml`
- Modify `README.md`
- Modify AI-Infra compose/config if needed

Add `/data` volume and document the Markdown/retrieval workflow.

### Verification

Run:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -q
docker compose -f docker-compose.prod.yml config
docker build --network host --build-arg UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple --build-arg UV_HTTP_TIMEOUT=240 -t bili-subtitle-service:test .
```

Deploy:

```bash
docker tag bili-subtitle-service:test 007hikari/bili-subtitle-service:latest
docker compose -f /home/hikari/projects/AI-Infra/services/docker-compose.yml up -d --force-recreate bili-subtitle-service bili-subtitle-service-mcp
curl -fsS http://127.0.0.1:8310/v1/health
/opt/data/bin/hermes mcp test bili_subtitle
```
