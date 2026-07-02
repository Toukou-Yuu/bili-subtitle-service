from fastapi.testclient import TestClient

from bili_subtitle_service.app import create_app
from bili_subtitle_service.models import (
    ExtractResponse,
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
