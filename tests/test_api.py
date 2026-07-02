from fastapi.testclient import TestClient

from bili_subtitle_service.app import create_app
from bili_subtitle_service.models import (
    ExtractResponse,
    GetVideoNoteResponse,
    SaveVideoNoteRequest,
    SaveVideoNoteResponse,
    SubtitleMetadata,
    Transcript,
    VideoMetadata,
)


def test_get_extract_endpoint_returns_structured_payload() -> None:
    async def fake_extract(url: str, page: int | None = None) -> ExtractResponse:
        assert url == "https://www.bilibili.com/video/BV1qiKf65EW9"
        assert page is None
        return ExtractResponse(
            ok=True,
            video=VideoMetadata(
                title="测试标题",
                bvid="BV1qiKf65EW9",
                aid="123",
                cid="456",
                page_number=1,
                part_title="正片",
            ),
            subtitle=SubtitleMetadata(
                language="中文",
                is_ai=True,
                source_url="https://example.test/sub.json",
                row_count=3,
            ),
            transcript=Transcript(cleaned_text="字幕正文", char_count=4),
            warnings=[],
        )

    app = create_app(extract_func=fake_extract)
    client = TestClient(app)

    response = client.get(
        "/extract",
        params={"url": "https://www.bilibili.com/video/BV1qiKf65EW9"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["video"]["title"] == "测试标题"
    assert payload["video"]["part_title"] == "正片"
    assert payload["transcript"]["cleaned_text"] == "字幕正文"


def test_health_endpoint_reports_ok() -> None:
    app = create_app(extract_func=None)
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "bili-subtitle-service"}


def test_post_notes_from_url_returns_markdown_archive_result() -> None:
    async def fake_save(request: SaveVideoNoteRequest) -> SaveVideoNoteResponse:
        assert request.url == "https://b23.tv/snbsbAC"
        assert request.analysis == "AI 讲解"
        assert request.categories == ["哲学"]
        return SaveVideoNoteResponse(
            ok=True,
            document_id="bili_BV1qiKf65EW9_p1",
            markdown_path="/data/library/2026/07/bili_BV1qiKf65EW9_p1.md",
            retrieval_synced=True,
            retrieval_collection="bili_video_notes",
            warnings=["使用自动字幕"],
        )

    app = create_app(save_note_func=fake_save)
    client = TestClient(app)

    response = client.post(
        "/notes/from-url",
        json={
            "url": "https://b23.tv/snbsbAC",
            "analysis": "AI 讲解",
            "categories": ["哲学"],
            "tags": ["个性化"],
            "profile_signals": ["关注欲望生产"],
            "sync_retrieval": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == "bili_BV1qiKf65EW9_p1"
    assert payload["retrieval_synced"] is True


def test_get_note_returns_saved_markdown() -> None:
    async def fake_get(document_id: str) -> GetVideoNoteResponse:
        assert document_id == "bili_BV1qiKf65EW9_p1"
        return GetVideoNoteResponse(
            ok=True,
            document_id=document_id,
            markdown_path="/data/library/2026/07/bili_BV1qiKf65EW9_p1.md",
            markdown="# 标题\n\n## 字幕正文",
            metadata={"title": "标题"},
        )

    app = create_app(get_note_func=fake_get)
    client = TestClient(app)

    response = client.get("/notes/bili_BV1qiKf65EW9_p1")

    assert response.status_code == 200
    assert response.json()["metadata"]["title"] == "标题"
