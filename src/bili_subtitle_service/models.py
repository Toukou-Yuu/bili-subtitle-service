from __future__ import annotations

from pydantic import BaseModel, Field


class VideoReference(BaseModel):
    bvid: str
    page_number: int = 1
    source_url: str
    resolved_url: str | None = None


class VideoMetadata(BaseModel):
    title: str
    bvid: str
    aid: str
    cid: str
    page_number: int
    part_title: str | None = None


class SubtitleMetadata(BaseModel):
    language: str
    is_ai: bool
    source_url: str
    row_count: int


class Transcript(BaseModel):
    cleaned_text: str
    char_count: int = Field(ge=0)


class ExtractResponse(BaseModel):
    ok: bool = True
    video: VideoMetadata
    subtitle: SubtitleMetadata
    transcript: Transcript
    warnings: list[str] = Field(default_factory=list)


class SaveVideoNoteRequest(BaseModel):
    url: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    analysis: str = ""
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    profile_signals: list[str] = Field(default_factory=list)
    sync_retrieval: bool | None = None


class SaveVideoNoteResponse(BaseModel):
    ok: bool = True
    document_id: str
    markdown_path: str
    retrieval_synced: bool = False
    retrieval_collection: str | None = None
    warnings: list[str] = Field(default_factory=list)


class GetVideoNoteResponse(BaseModel):
    ok: bool = True
    document_id: str
    markdown_path: str
    markdown: str
    metadata: dict[str, object] = Field(default_factory=dict)
