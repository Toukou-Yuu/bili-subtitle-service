from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from bili_subtitle_service.extractor import SubtitleExtractionError, extract_subtitle
from bili_subtitle_service.models import ExtractResponse

ExtractFunc = Callable[[str, int | None], Awaitable[ExtractResponse]]


async def _default_extract(url: str, page: int | None = None) -> ExtractResponse:
    return await extract_subtitle(url, page=page)


def create_app(extract_func: ExtractFunc | None = None) -> FastAPI:
    app = FastAPI(title="bili-subtitle-service", version="0.1.0")
    handler = extract_func or _default_extract

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

    return app


app = create_app()
