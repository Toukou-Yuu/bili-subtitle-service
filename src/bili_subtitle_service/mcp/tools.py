from __future__ import annotations

from typing import Any

from bili_subtitle_service.extractor import SubtitleExtractionError, extract_subtitle
from bili_subtitle_service.models import SaveVideoNoteRequest
from bili_subtitle_service.notes import get_video_note_response, save_video_note_from_request

ToolResult = dict[str, Any]


def success(summary: str, data: dict[str, Any], warnings: list[str] | None = None) -> ToolResult:
    return {"ok": True, "summary": summary, "data": data, "warnings": warnings or []}


def error(*, code: str, message: str, retryable: bool, suggested_action: str) -> ToolResult:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "suggested_action": suggested_action,
        },
    }


async def extract_subtitle_tool(url: str, page: int | None = None) -> ToolResult:
    try:
        result = await extract_subtitle(url, page=page)
    except ValueError as exc:
        return error(
            code="invalid_input",
            message=str(exc),
            retryable=False,
            suggested_action="检查 Bilibili 链接或分P参数后重试。",
        )
    except (SubtitleExtractionError, Exception) as exc:  # noqa: BLE001 - MCP tools should return typed errors.
        return error(
            code="extract_failed",
            message=str(exc),
            retryable=True,
            suggested_action="稍后重试；如果仍失败，请让用户提供字幕文本或确认视频存在可用字幕。",
        )

    return success(
        f"Extracted Bilibili subtitle for {result.video.title} P{result.video.page_number}.",
        result.model_dump(mode="json"),
        result.warnings,
    )


async def save_video_note_tool(
    url: str,
    analysis: str = "",
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    profile_signals: list[str] | None = None,
    page: int | None = None,
    sync_retrieval: bool | None = None,
) -> ToolResult:
    try:
        result = await save_video_note_from_request(
            SaveVideoNoteRequest(
                url=url,
                page=page,
                analysis=analysis,
                categories=categories or [],
                tags=tags or [],
                profile_signals=profile_signals or [],
                sync_retrieval=sync_retrieval,
            )
        )
    except ValueError as exc:
        return error(
            code="invalid_input",
            message=str(exc),
            retryable=False,
            suggested_action="检查链接、分P或分类字段后重试。",
        )
    except (SubtitleExtractionError, FileNotFoundError, RuntimeError, Exception) as exc:  # noqa: BLE001
        return error(
            code="save_note_failed",
            message=str(exc),
            retryable=True,
            suggested_action="确认字幕可提取、持久化目录可写，并检查 retrieval 服务状态。",
        )

    return success(
        f"Saved Bilibili video note {result.document_id}.",
        result.model_dump(mode="json"),
        result.warnings,
    )


async def get_video_note_tool(document_id: str) -> ToolResult:
    try:
        result = await get_video_note_response(document_id)
    except ValueError as exc:
        return error(
            code="invalid_input",
            message=str(exc),
            retryable=False,
            suggested_action="检查 document_id 是否为 save_video_note 返回的值。",
        )
    except FileNotFoundError as exc:
        return error(
            code="note_not_found",
            message=str(exc),
            retryable=False,
            suggested_action="先保存视频笔记，或检查 document_id。",
        )

    return success(
        f"Loaded Bilibili video note {result.document_id}.",
        result.model_dump(mode="json"),
    )
