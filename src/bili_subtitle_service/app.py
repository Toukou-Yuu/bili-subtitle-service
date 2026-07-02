from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from bili_subtitle_service.extractor import SubtitleExtractionError, extract_subtitle
from bili_subtitle_service.models import (
    ExtractResponse,
    GetVideoNoteResponse,
    SaveVideoNoteRequest,
    SaveVideoNoteResponse,
)
from bili_subtitle_service.notes import get_video_note_response, save_video_note_from_request

ExtractFunc = Callable[[str, int | None], Awaitable[ExtractResponse]]
SaveNoteFunc = Callable[[SaveVideoNoteRequest], Awaitable[SaveVideoNoteResponse]]
GetNoteFunc = Callable[[str], Awaitable[GetVideoNoteResponse]]


async def _default_extract(url: str, page: int | None = None) -> ExtractResponse:
    return await extract_subtitle(url, page=page)


async def _default_save_note(request: SaveVideoNoteRequest) -> SaveVideoNoteResponse:
    return await save_video_note_from_request(request)


async def _default_get_note(document_id: str) -> GetVideoNoteResponse:
    return await get_video_note_response(document_id)


def create_app(
    extract_func: ExtractFunc | None = None,
    save_note_func: SaveNoteFunc | None = None,
    get_note_func: GetNoteFunc | None = None,
) -> FastAPI:
    app = FastAPI(title="bili-subtitle-service", version="0.1.0")
    handler = extract_func or _default_extract
    save_handler = save_note_func or _default_save_note
    get_handler = get_note_func or _default_get_note

    @app.get("/v1/health")
    async def health() -> dict[str, bool | str]:
        return {"ok": True, "service": "bili-subtitle-service"}

    @app.get("/healthz")
    async def healthz() -> dict[str, bool | str]:
        return await health()

    @app.get("/extract", response_model=ExtractResponse)
    async def extract_endpoint(
        url: Annotated[str, Query(min_length=1)],
        page: Annotated[int | None, Query(ge=1)] = None,
    ) -> ExtractResponse:
        try:
            return await handler(url, page)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SubtitleExtractionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/notes/from-url", response_model=SaveVideoNoteResponse)
    async def save_note_endpoint(request: SaveVideoNoteRequest) -> SaveVideoNoteResponse:
        try:
            return await save_handler(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SubtitleExtractionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/notes/{document_id}", response_model=GetVideoNoteResponse)
    async def get_note_endpoint(document_id: str) -> GetVideoNoteResponse:
        try:
            return await get_handler(document_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
