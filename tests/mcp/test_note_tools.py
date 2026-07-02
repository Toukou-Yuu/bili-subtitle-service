import pytest

from bili_subtitle_service.mcp import tools
from bili_subtitle_service.models import GetVideoNoteResponse, SaveVideoNoteResponse


@pytest.mark.asyncio
async def test_save_video_note_tool_returns_archive_result(monkeypatch) -> None:
    async def fake_save(request):
        assert request.url == "https://b23.tv/snbsbAC"
        assert request.analysis == "AI 分析"
        assert request.categories == ["哲学"]
        return SaveVideoNoteResponse(
            ok=True,
            document_id="bili_BV1qiKf65EW9_p1",
            markdown_path="/data/library/2026/07/bili_BV1qiKf65EW9_p1.md",
            retrieval_synced=True,
            retrieval_collection="bili_video_notes",
            warnings=[],
        )

    monkeypatch.setattr(tools, "save_video_note_from_request", fake_save)

    result = await tools.save_video_note_tool(
        "https://b23.tv/snbsbAC",
        analysis="AI 分析",
        categories=["哲学"],
        tags=["个性化"],
        profile_signals=["关注欲望生产"],
        sync_retrieval=True,
    )

    assert result["ok"] is True
    assert result["data"]["document_id"] == "bili_BV1qiKf65EW9_p1"
    assert result["data"]["retrieval_synced"] is True


@pytest.mark.asyncio
async def test_get_video_note_tool_returns_markdown(monkeypatch) -> None:
    async def fake_get(document_id):
        return GetVideoNoteResponse(
            ok=True,
            document_id=document_id,
            markdown_path="/data/library/note.md",
            markdown="# 标题",
            metadata={"title": "标题"},
        )

    monkeypatch.setattr(tools, "get_video_note_response", fake_get)

    result = await tools.get_video_note_tool("bili_BV1qiKf65EW9_p1")

    assert result["ok"] is True
    assert result["data"]["markdown"] == "# 标题"
