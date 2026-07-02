from pathlib import Path

from bili_subtitle_service.models import (
    ExtractResponse,
    SubtitleMetadata,
    Transcript,
    VideoMetadata,
)
from bili_subtitle_service.notes import VideoNoteArchive, build_document_id


def make_extraction() -> ExtractResponse:
    return ExtractResponse(
        ok=True,
        video=VideoMetadata(
            title="个性化如何导致扭曲与控制？",
            bvid="BV1qiKf65EW9",
            aid="116838981704609",
            cid="39535709303",
            page_number=1,
            part_title="正片",
        ),
        subtitle=SubtitleMetadata(
            language="中文",
            is_ai=True,
            source_url="https://aisubtitle.hdslb.com/subtitle.json?auth_key=secret-token",
            row_count=331,
        ),
        transcript=Transcript(cleaned_text="第一行字幕\n第二行字幕", char_count=9),
        warnings=["使用自动字幕"],
    )


def test_build_document_id_is_stable_and_path_safe() -> None:
    assert build_document_id("BV1qiKf65EW9", 1) == "bili_BV1qiKf65EW9_p1"


def test_video_note_archive_writes_markdown_without_ephemeral_subtitle_url(tmp_path: Path) -> None:
    archive = VideoNoteArchive(tmp_path)

    note = archive.save(
        make_extraction(),
        source_url="https://b23.tv/snbsbAC",
        analysis="这是 AI 讲解分析。",
        categories=["哲学", "资本主义批判"],
        tags=["个性化", "人形洞"],
        profile_signals=["关注欲望如何被市场塑造"],
        captured_at="2026-07-02T22:30:00+00:00",
        analysis_model="deepseek-v4-flash",
        analysis_reasoning_effort="high",
    )

    assert note.document_id == "bili_BV1qiKf65EW9_p1"
    assert note.markdown_path == tmp_path / "2026" / "07" / "bili_BV1qiKf65EW9_p1.md"
    text = note.markdown_path.read_text(encoding="utf-8")
    assert "# 个性化如何导致扭曲与控制？" in text
    assert "## AI 讲解分析" in text
    assert "这是 AI 讲解分析。" in text
    assert "## 字幕正文" in text
    assert "第一行字幕" in text
    assert "profile_signals:" in text
    assert "关注欲望如何被市场塑造" in text
    assert "auth_key" not in text
    assert "secret-token" not in text


def test_video_note_archive_can_read_saved_note(tmp_path: Path) -> None:
    archive = VideoNoteArchive(tmp_path)
    saved = archive.save(
        make_extraction(),
        source_url="https://www.bilibili.com/video/BV1qiKf65EW9",
        analysis="分析正文",
        categories=[],
        tags=[],
        profile_signals=[],
        captured_at="2026-07-02T22:30:00+00:00",
        analysis_model=None,
        analysis_reasoning_effort=None,
    )

    loaded = archive.get(saved.document_id)

    assert loaded.document_id == saved.document_id
    assert loaded.markdown_path == saved.markdown_path
    assert "分析正文" in loaded.markdown
