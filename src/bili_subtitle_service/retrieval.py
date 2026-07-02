from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from bili_subtitle_service.config import RetrievalConfig
from bili_subtitle_service.notes import SavedVideoNote


@dataclass(frozen=True)
class RetrievalSyncResult:
    synced: bool
    collection: str
    accepted: int = 0
    upserted: int = 0
    skipped: int = 0
    response: dict[str, Any] | None = None


class RetrievalSyncClient:
    def __init__(
        self,
        config: RetrievalConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._client = client

    async def sync_note(self, note: SavedVideoNote) -> RetrievalSyncResult:
        if not self.config.enabled:
            return RetrievalSyncResult(synced=False, collection=self.config.collection)

        client = self._client
        if client is None:
            async with httpx.AsyncClient(timeout=30) as owned_client:
                return await self._sync_note_with_client(owned_client, note)
        return await self._sync_note_with_client(client, note)

    async def _sync_note_with_client(
        self,
        client: httpx.AsyncClient,
        note: SavedVideoNote,
    ) -> RetrievalSyncResult:
        await self._ensure_collection(client)
        response = await client.post(
            f"{self.config.base_url}/documents/upsert",
            json={
                "collection": self.config.collection,
                "documents": [self._document_payload(note)],
                "indexing": {"mode": "sync"},
            },
        )
        response.raise_for_status()
        data = response.json()
        return RetrievalSyncResult(
            synced=True,
            collection=self.config.collection,
            accepted=int(data.get("accepted") or 0),
            upserted=int(data.get("upserted") or 0),
            skipped=int(data.get("skipped") or 0),
            response=data if isinstance(data, dict) else None,
        )

    async def _ensure_collection(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            f"{self.config.base_url}/collections",
            json={
                "name": self.config.collection,
                "description": "Bilibili video notes: transcript plus AI analysis",
                "chunk_strategy": "markdown_semantic",
            },
        )
        response.raise_for_status()

    def _document_payload(self, note: SavedVideoNote) -> dict[str, Any]:
        title = str(note.metadata.get("title") or note.document_id)
        metadata = {
            **note.metadata,
            "source": "bilibili",
            "doc_type": "bili_video_note",
            "source_type": "mixed_transcript_and_ai_analysis",
            "document_id": note.document_id,
            "markdown_path": str(note.markdown_path),
        }
        return {
            "id": note.document_id,
            "source": "bilibili",
            "doc_type": "bili_video_note",
            "title": title,
            "text": note.markdown,
            "metadata": metadata,
        }
