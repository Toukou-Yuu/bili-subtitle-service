from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from bili_subtitle_service.config import AppConfig
from bili_subtitle_service.models import (
    ExtractResponse,
    SubtitleMetadata,
    Transcript,
    VideoMetadata,
    VideoReference,
)
from bili_subtitle_service.text import clean_subtitle_text
from bili_subtitle_service.wbi import make_mixin_key, sign_wbi_params

BVID_RE = re.compile(r"BV[0-9A-Za-z]+")
BILIBILI_API_BASE = "https://api.bilibili.com"


class SubtitleExtractionError(RuntimeError):
    pass


def parse_bilibili_url(url: str) -> VideoReference:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    bvid_values = query.get("bvid")
    bvid: str | None = bvid_values[0] if bvid_values else None

    if not bvid:
        match = BVID_RE.search(parsed.path)
        bvid = match.group(0) if match else None

    if not bvid:
        raise ValueError("未识别到 Bilibili bvid")

    page_number = 1
    page_values = query.get("p")
    if page_values and page_values[0]:
        raw_page = page_values[0]
        if not raw_page.isdigit() or int(raw_page) < 1:
            raise ValueError(f"当前分P参数无效：p={raw_page}")
        page_number = int(raw_page)

    return VideoReference(bvid=bvid, page_number=page_number, source_url=url)


class BiliSubtitleExtractor:
    def __init__(
        self,
        config: AppConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or AppConfig.from_env()
        self._client = client
        self._wbi_mixin_key: str | None = None

    async def extract(self, url: str, page: int | None = None) -> ExtractResponse:
        client = self._client
        if client is None:
            async with self._new_client() as owned_client:
                return await self._extract_with_client(owned_client, url, page)
        return await self._extract_with_client(client, url, page)

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.config.fetch.timeout_seconds,
            follow_redirects=True,
            proxy=self.config.fetch.proxy,
            headers={"User-Agent": self.config.fetch.user_agent},
        )

    async def _extract_with_client(
        self, client: httpx.AsyncClient, url: str, page: int | None
    ) -> ExtractResponse:
        reference = await self._resolve_reference(client, url)
        if page is not None:
            if page < 1:
                raise ValueError(f"当前分P参数无效：p={page}")
            reference = reference.model_copy(update={"page_number": page})
        referer = reference.resolved_url or reference.source_url

        video_info = await self._get_video_info(client, reference)
        pages = video_info.get("pages") or []
        if not isinstance(pages, list) or not pages:
            raise SubtitleExtractionError("未获取到分P信息")
        if reference.page_number > len(pages):
            raise SubtitleExtractionError(
                f"当前 URL 指向第 {reference.page_number} P，但接口只返回 {len(pages)} 个分P"
            )

        page_info = pages[reference.page_number - 1]
        cid = str(page_info.get("cid") or "")
        if not cid:
            raise SubtitleExtractionError(f"未获取到第 {reference.page_number} P 的 cid")

        aid = str(video_info.get("aid") or "")
        subtitles = await self._get_subtitle_list(client, aid=aid, cid=cid, referer=referer)
        selected = pick_best_subtitle(subtitles)
        if not selected:
            raise SubtitleExtractionError(
                "未找到带链接的可用字幕；如果浏览器登录后能看到字幕，请通过 "
                "BILI_SUBTITLE_COOKIE_FILE 或 BILI_SUBTITLE_COOKIE 配置 Bilibili 登录 Cookie"
            )

        subtitle_url = normalize_subtitle_url(str(selected.get("subtitle_url") or ""), url)
        subtitle_json = await self._request_json(client, subtitle_url, referer=referer)
        text_items = validate_subtitle_body(subtitle_json.get("body"))
        cleaned_text = clean_subtitle_text(text_items)
        if not cleaned_text:
            raise SubtitleExtractionError("清洗后字幕为空")

        language = str(selected.get("lan_doc") or selected.get("lan") or "未知语言")
        is_ai = selected.get("ai_status") != 0
        warnings = ["使用自动字幕"] if is_ai else []

        return ExtractResponse(
            ok=True,
            video=VideoMetadata(
                title=str(video_info.get("title") or "当前视频").strip(),
                bvid=str(video_info.get("bvid") or reference.bvid),
                aid=aid,
                cid=cid,
                page_number=reference.page_number,
                part_title=(str(page_info.get("part") or "").strip() or None),
            ),
            subtitle=SubtitleMetadata(
                language=language,
                is_ai=is_ai,
                source_url=subtitle_url,
                row_count=len(text_items),
            ),
            transcript=Transcript(cleaned_text=cleaned_text, char_count=len(cleaned_text)),
            warnings=warnings,
        )

    async def _resolve_reference(self, client: httpx.AsyncClient, url: str) -> VideoReference:
        try:
            return parse_bilibili_url(url)
        except ValueError:
            response = await client.get(
                url,
                follow_redirects=False,
                headers=self._headers(url),
            )
            location = response.headers.get("location")
            resolved = urljoin(url, location) if location else str(response.url)
            reference = parse_bilibili_url(resolved)
            return reference.model_copy(update={"source_url": url, "resolved_url": resolved})

    async def _get_video_info(
        self, client: httpx.AsyncClient, reference: VideoReference
    ) -> dict[str, Any]:
        data = await self._request_json(
            client,
            f"{BILIBILI_API_BASE}/x/web-interface/view",
            params={"bvid": reference.bvid},
            referer=reference.source_url,
        )
        if data.get("code") != 0:
            raise SubtitleExtractionError(str(data.get("message") or "获取视频信息失败"))
        info = data.get("data")
        if not isinstance(info, dict):
            raise SubtitleExtractionError("视频信息格式异常")
        if str(info.get("bvid") or reference.bvid) != reference.bvid:
            raise SubtitleExtractionError(
                f"接口返回的 bvid 与当前 URL 不一致：{info.get('bvid')} !== {reference.bvid}"
            )
        return info

    async def _get_subtitle_list(
        self, client: httpx.AsyncClient, *, aid: str, cid: str, referer: str
    ) -> list[dict[str, Any]]:
        params: dict[str, object] = {"aid": aid, "cid": cid}
        signed_params = await self._sign_wbi_params(client, params, referer=referer)
        data = await self._request_json(
            client,
            f"{BILIBILI_API_BASE}/x/player/wbi/v2",
            params=signed_params,
            referer=referer,
        )
        if data.get("code") != 0:
            raise SubtitleExtractionError(str(data.get("message") or "获取字幕列表失败"))
        subtitles = ((data.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
        if not isinstance(subtitles, list):
            raise SubtitleExtractionError("字幕列表格式异常")
        return [item for item in subtitles if isinstance(item, dict)]

    async def _sign_wbi_params(
        self,
        client: httpx.AsyncClient,
        params: dict[str, object],
        *,
        referer: str,
    ) -> dict[str, str]:
        mixin_key = await self._get_wbi_mixin_key(client, referer=referer)
        return sign_wbi_params(params, mixin_key=mixin_key)

    async def _get_wbi_mixin_key(self, client: httpx.AsyncClient, *, referer: str) -> str:
        if self._wbi_mixin_key:
            return self._wbi_mixin_key
        data = await self._request_json(
            client,
            f"{BILIBILI_API_BASE}/x/web-interface/nav",
            referer="https://www.bilibili.com/",
        )
        wbi_img = (data.get("data") or {}).get("wbi_img") or {}
        img_key = _extract_wbi_key(str(wbi_img.get("img_url") or ""))
        sub_key = _extract_wbi_key(str(wbi_img.get("sub_url") or ""))
        self._wbi_mixin_key = make_mixin_key(img_key, sub_key)
        return self._wbi_mixin_key

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        referer: str | None = None,
    ) -> dict[str, Any]:
        try:
            response = await client.get(url, params=params, headers=self._headers(referer))
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SubtitleExtractionError(
                f"请求失败：{exc.response.status_code} {exc.request.url}"
            ) from exc
        except httpx.RequestError as exc:
            raise SubtitleExtractionError(f"网络请求失败：{exc.request.url}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise SubtitleExtractionError("接口返回不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise SubtitleExtractionError("接口返回 JSON 格式异常")
        return payload

    def _headers(self, referer: str | None = None) -> dict[str, str]:
        headers = {
            "User-Agent": self.config.fetch.user_agent,
            "Referer": referer or "https://www.bilibili.com/",
        }
        if self.config.fetch.cookie:
            headers["Cookie"] = self.config.fetch.cookie
        return headers


def _extract_wbi_key(url: str) -> str:
    key = PurePosixPath(urlparse(url).path).stem
    if not key:
        raise SubtitleExtractionError("未获取到 WBI 签名 key")
    return key


def pick_best_subtitle(subtitles: list[dict[str, Any]]) -> dict[str, Any] | None:
    def score(item: dict[str, Any]) -> int:
        text = f"{item.get('lan') or ''} {item.get('lan_doc') or ''}".lower()
        value = 0
        if re.search(r"zh-cn|zh-hans|zh|cn|中文|简体", text):
            value += 100
        if re.search(r"中文|简体", text):
            value += 20
        if re.search(r"ai|自动|智能", text):
            value -= 10
        if item.get("id_str"):
            value += 1
        if item.get("ai_status") == 0:
            value += 5
        return value

    candidates = [item for item in subtitles if item.get("subtitle_url")]
    if not candidates:
        return None
    return sorted(candidates, key=score, reverse=True)[0]


def normalize_subtitle_url(subtitle_url: str, base_url: str) -> str:
    if not subtitle_url:
        raise SubtitleExtractionError("字幕链接为空")
    if subtitle_url.startswith("//"):
        return f"https:{subtitle_url}"
    if re.match(r"^https?://", subtitle_url, flags=re.I):
        return subtitle_url
    if re.match(r"^[a-z0-9.-]+/", subtitle_url, flags=re.I):
        return f"https://{subtitle_url}"
    return urljoin(base_url, subtitle_url)


def validate_subtitle_body(body: Any) -> list[str]:
    if not isinstance(body, list) or not body:
        raise SubtitleExtractionError("字幕内容为空")
    text_items = [str(item.get("content") or "").strip() for item in body if isinstance(item, dict)]
    text_items = [item for item in text_items if item]
    if not text_items:
        raise SubtitleExtractionError("字幕正文为空")
    if len(text_items) < 3:
        raise SubtitleExtractionError(f"字幕行数过少：{len(text_items)} 行")
    return text_items


async def extract_subtitle(url: str, page: int | None = None) -> ExtractResponse:
    return await BiliSubtitleExtractor().extract(url, page=page)
