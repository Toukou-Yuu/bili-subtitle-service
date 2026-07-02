from __future__ import annotations

from typing import Any

from bili_subtitle_service.extractor import SubtitleExtractionError, extract_subtitle

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
