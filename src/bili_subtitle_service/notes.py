from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from bili_subtitle_service.config import AppConfig
from bili_subtitle_service.extractor import extract_subtitle
from bili_subtitle_service.models import (
    ExtractResponse,
    GetVideoNoteResponse,
    SaveVideoNoteRequest,
    SaveVideoNoteResponse,
)

DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class SavedVideoNote:
    document_id: str
    markdown_path: Path
    markdown: str
    metadata: dict[str, Any]


def build_document_id(bvid: str, page_number: int) -> str:
    return f"bili_{bvid}_p{page_number}"


class VideoNoteArchive:
    def __init__(self, library_dir: Path | str) -> None:
        self.library_dir = Path(library_dir)

    def save(
        self,
        extraction: ExtractResponse,
        *,
        source_url: str,
        analysis: str,
        categories: list[str],
        tags: list[str],
        profile_signals: list[str],
        captured_at: str,
        analysis_model: str | None,
        analysis_reasoning_effort: str | None,
    ) -> SavedVideoNote:
        document_id = build_document_id(extraction.video.bvid, extraction.video.page_number)
        metadata = self._metadata(
            extraction,
            source_url=source_url,
            document_id=document_id,
            categories=categories,
            tags=tags,
            profile_signals=profile_signals,
            captured_at=captured_at,
            analysis_model=analysis_model,
            analysis_reasoning_effort=analysis_reasoning_effort,
            contains_ai_analysis=bool(analysis.strip()),
        )
        markdown = render_markdown_note(
            extraction,
            metadata=metadata,
            analysis=analysis,
            categories=categories,
            tags=tags,
            profile_signals=profile_signals,
        )
        path = self._path_for(document_id, captured_at)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        return SavedVideoNote(
            document_id=document_id,
            markdown_path=path,
            markdown=markdown,
            metadata=metadata,
        )

    def get(self, document_id: str) -> SavedVideoNote:
        if not DOCUMENT_ID_RE.fullmatch(document_id):
            raise ValueError(f"invalid document_id: {document_id}")
        matches = sorted(self.library_dir.glob(f"**/{document_id}.md"))
        if not matches:
            raise FileNotFoundError(f"video note not found: {document_id}")
        path = matches[-1]
        markdown = path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(markdown)
        return SavedVideoNote(
            document_id=document_id, markdown_path=path, markdown=markdown, metadata=metadata
        )

    def _path_for(self, document_id: str, captured_at: str) -> Path:
        year = captured_at[:4] if len(captured_at) >= 4 else "unknown"
        month = captured_at[5:7] if len(captured_at) >= 7 else "unknown"
        return self.library_dir / year / month / f"{document_id}.md"

    def _metadata(
        self,
        extraction: ExtractResponse,
        *,
        source_url: str,
        document_id: str,
        categories: list[str],
        tags: list[str],
        profile_signals: list[str],
        captured_at: str,
        analysis_model: str | None,
        analysis_reasoning_effort: str | None,
        contains_ai_analysis: bool,
    ) -> dict[str, Any]:
        return {
            "type": "bili_video_note",
            "source": "bilibili",
            "document_id": document_id,
            "bvid": extraction.video.bvid,
            "aid": extraction.video.aid,
            "cid": extraction.video.cid,
            "page_number": extraction.video.page_number,
            "title": extraction.video.title,
            "part_title": extraction.video.part_title,
            "url": source_url,
            "captured_at": captured_at,
            "subtitle_language": extraction.subtitle.language,
            "subtitle_is_ai": extraction.subtitle.is_ai,
            "subtitle_row_count": extraction.subtitle.row_count,
            "transcript_char_count": extraction.transcript.char_count,
            "categories": categories,
            "tags": tags,
            "profile_signals": profile_signals,
            "analysis_model": analysis_model,
            "analysis_reasoning_effort": analysis_reasoning_effort,
            "contains_ai_analysis": contains_ai_analysis,
        }


def render_markdown_note(
    extraction: ExtractResponse,
    *,
    metadata: dict[str, Any],
    analysis: str,
    categories: list[str],
    tags: list[str],
    profile_signals: list[str],
) -> str:
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    analysis_text = analysis.strip() or "（尚未填写 AI 讲解分析）"
    category_text = _bullet_list(categories) or "- （未分类）"
    tag_text = _bullet_list(tags) or "- （无标签）"
    profile_text = _bullet_list(profile_signals) or "- （暂无画像信号）"
    lines = [
        "---",
        frontmatter,
        "---",
        "",
        f"# {extraction.video.title}",
        "",
        "## Metadata",
        "",
        f"- BVID: `{extraction.video.bvid}`",
        f"- AID: `{extraction.video.aid}`",
        f"- CID: `{extraction.video.cid}`",
        f"- 分P: {extraction.video.page_number}",
        f"- 分P标题: {extraction.video.part_title or '正片'}",
        f"- 字幕语言: {extraction.subtitle.language}",
        f"- 自动字幕: {'是' if extraction.subtitle.is_ai else '否'}",
        f"- 字幕行数: {extraction.subtitle.row_count}",
        f"- 字幕字符数: {extraction.transcript.char_count}",
        f"- 抓取时间: {metadata['captured_at']}",
        "",
        "## AI 讲解分析",
        "",
        analysis_text,
        "",
        "## 分类与画像信号",
        "",
        "### 类别",
        "",
        category_text,
        "",
        "### 标签",
        "",
        tag_text,
        "",
        "### 用户画像信号",
        "",
        profile_text,
        "",
        "## 字幕正文",
        "",
        "```text",
        extraction.transcript.cleaned_text,
        "```",
        "",
    ]
    return "\n".join(lines)


def parse_frontmatter(markdown: str) -> dict[str, Any]:
    if not markdown.startswith("---\n"):
        return {}
    _, frontmatter, _body = markdown.split("---", 2)
    data = yaml.safe_load(frontmatter) or {}
    return data if isinstance(data, dict) else {}


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if item.strip())


async def save_video_note_from_request(
    request: SaveVideoNoteRequest,
    config: AppConfig | None = None,
) -> SaveVideoNoteResponse:
    runtime_config = config or AppConfig.from_env()
    if not runtime_config.storage.enabled:
        raise RuntimeError("storage is disabled")

    extraction = await extract_subtitle(request.url, page=request.page)
    captured_at = datetime.now(UTC).isoformat()
    archive = VideoNoteArchive(runtime_config.storage.library_dir)
    note = archive.save(
        extraction,
        source_url=request.url,
        analysis=request.analysis,
        categories=request.categories,
        tags=request.tags,
        profile_signals=request.profile_signals,
        captured_at=captured_at,
        analysis_model=runtime_config.summary.model,
        analysis_reasoning_effort=runtime_config.summary.reasoning_effort,
    )

    should_sync = request.sync_retrieval
    if should_sync is None:
        should_sync = runtime_config.retrieval.sync_by_default

    retrieval_synced = False
    retrieval_collection: str | None = None
    if should_sync and runtime_config.retrieval.enabled:
        from bili_subtitle_service.retrieval import RetrievalSyncClient

        result = await RetrievalSyncClient(runtime_config.retrieval).sync_note(note)
        retrieval_synced = result.synced
        retrieval_collection = result.collection

    return SaveVideoNoteResponse(
        ok=True,
        document_id=note.document_id,
        markdown_path=str(note.markdown_path),
        retrieval_synced=retrieval_synced,
        retrieval_collection=retrieval_collection,
        warnings=extraction.warnings,
    )


async def get_video_note_response(
    document_id: str,
    config: AppConfig | None = None,
) -> GetVideoNoteResponse:
    runtime_config = config or AppConfig.from_env()
    note = VideoNoteArchive(runtime_config.storage.library_dir).get(document_id)
    return GetVideoNoteResponse(
        ok=True,
        document_id=note.document_id,
        markdown_path=str(note.markdown_path),
        markdown=note.markdown,
        metadata=note.metadata,
    )
