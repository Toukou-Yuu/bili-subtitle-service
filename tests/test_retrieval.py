import json

import httpx
import pytest

from bili_subtitle_service.config import RetrievalConfig
from bili_subtitle_service.notes import SavedVideoNote
from bili_subtitle_service.retrieval import RetrievalSyncClient


@pytest.mark.asyncio
async def test_retrieval_sync_creates_collection_and_upserts_markdown_note(tmp_path) -> None:
    requests: list[tuple[str, str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode() or "{}")
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/v1/collections":
            return httpx.Response(200, json={"name": body["name"], "created": True})
        if request.url.path == "/v1/documents/upsert":
            return httpx.Response(
                200,
                json={"collection": body["collection"], "accepted": 1, "upserted": 1, "skipped": 0},
            )
        return httpx.Response(404, json={"detail": "unexpected"})

    note = SavedVideoNote(
        document_id="bili_BV1qiKf65EW9_p1",
        markdown_path=tmp_path / "note.md",
        markdown="# 标题\n\n## AI 讲解分析\n\n分析\n\n## 字幕正文\n\n字幕",
        metadata={
            "title": "标题",
            "bvid": "BV1qiKf65EW9",
            "aid": "123",
            "cid": "456",
            "page_number": 1,
            "categories": ["哲学"],
            "tags": ["个性化"],
            "profile_signals": ["关注市场塑造欲望"],
            "contains_ai_analysis": True,
        },
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sync = RetrievalSyncClient(
            RetrievalConfig(
                enabled=True,
                base_url="http://retrieval-api:8000/v1",
                collection="bili_video_notes",
            ),
            client=client,
        )
        result = await sync.sync_note(note)

    assert result.synced is True
    assert result.collection == "bili_video_notes"
    assert requests[0] == (
        "POST",
        "/v1/collections",
        {
            "name": "bili_video_notes",
            "description": "Bilibili video notes: transcript plus AI analysis",
            "chunk_strategy": "markdown_semantic",
        },
    )
    upsert = requests[1][2]
    assert requests[1][0:2] == ("POST", "/v1/documents/upsert")
    assert upsert["collection"] == "bili_video_notes"
    assert upsert["indexing"] == {"mode": "sync"}
    document = upsert["documents"][0]
    assert document["id"] == "bili_BV1qiKf65EW9_p1"
    assert document["source"] == "bilibili"
    assert document["doc_type"] == "bili_video_note"
    assert document["title"] == "标题"
    assert document["text"] == note.markdown
    assert document["metadata"]["source_type"] == "mixed_transcript_and_ai_analysis"
    assert document["metadata"]["contains_ai_analysis"] is True
    assert document["metadata"]["categories"] == ["哲学"]
