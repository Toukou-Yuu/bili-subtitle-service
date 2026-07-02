import httpx
import pytest

from bili_subtitle_service.config import AppConfig
from bili_subtitle_service.extractor import BiliSubtitleExtractor

VIDEO_URL = "https://www.bilibili.com/list/watchlater?bvid=BV1qiKf65EW9&oid=116838981704609"
MOBILE_URL = "https://b23.tv/snbsbAC"


def make_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.startswith("https://b23.tv/snbsbAC"):
            return httpx.Response(
                302,
                headers={
                    "Location": "https://www.bilibili.com/video/BV1qiKf65EW9/?share_source=copy_web"
                },
            )
        if url.startswith("https://api.bilibili.com/x/web-interface/view"):
            assert request.url.params["bvid"] == "BV1qiKf65EW9"
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "aid": 116838981704609,
                        "bvid": "BV1qiKf65EW9",
                        "title": "个性化如何导致扭曲与控制？无法抵抗的人形洞诱惑",
                        "pages": [
                            {"cid": 321, "page": 1, "part": "正片"},
                        ],
                    },
                },
            )
        if url.startswith("https://api.bilibili.com/x/web-interface/nav"):
            return httpx.Response(
                200,
                json={
                    "code": -101,
                    "message": "账号未登录",
                    "data": {
                        "wbi_img": {
                            "img_url": "https://i0.hdslb.com/bfs/wbi/" + "a" * 64 + ".png",
                            "sub_url": "https://i0.hdslb.com/bfs/wbi/" + "b" * 64 + ".png",
                        }
                    },
                },
            )
        if url.startswith("https://api.bilibili.com/x/player/wbi/v2"):
            assert request.url.params["aid"] == "116838981704609"
            assert request.url.params["cid"] == "321"
            assert request.url.params.get("wts")
            assert request.url.params.get("w_rid")
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "subtitle": {
                            "subtitles": [
                                {
                                    "id": 1,
                                    "id_str": "1",
                                    "lan": "zh-CN",
                                    "lan_doc": "中文（自动生成）",
                                    "ai_status": 1,
                                    "subtitle_url": "//example.hdslb.com/subtitle.json",
                                }
                            ]
                        }
                    },
                },
            )
        if url == "https://example.hdslb.com/subtitle.json":
            return httpx.Response(
                200,
                json={
                    "body": [
                        {"from": 0, "to": 1, "content": "啊"},
                        {"from": 1, "to": 2, "content": "这个 个性化推荐会改变选择"},
                        {"from": 2, "to": 3, "content": "重点不是你喜欢什么"},
                        {"from": 3, "to": 4, "content": "，而是系统如何塑造你"},
                    ]
                },
            )
        return httpx.Response(404, text=f"unexpected URL: {url}")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_extract_from_watchlater_url_returns_clean_transcript_and_metadata() -> None:
    async with httpx.AsyncClient(transport=make_transport(), follow_redirects=True) as client:
        extractor = BiliSubtitleExtractor(AppConfig(), client=client)
        result = await extractor.extract(VIDEO_URL)

    assert result.video.title == "个性化如何导致扭曲与控制？无法抵抗的人形洞诱惑"
    assert result.video.part_title == "正片"
    assert result.video.bvid == "BV1qiKf65EW9"
    assert result.subtitle.language == "中文（自动生成）"
    assert result.transcript.cleaned_text == (
        "个性化推荐会改变选择\n重点不是你喜欢什么，而是系统如何塑造你"
    )
    assert result.transcript.char_count == len(result.transcript.cleaned_text)


@pytest.mark.asyncio
async def test_extract_from_mobile_short_link_follows_redirect() -> None:
    async with httpx.AsyncClient(transport=make_transport(), follow_redirects=True) as client:
        extractor = BiliSubtitleExtractor(AppConfig(), client=client)
        result = await extractor.extract(MOBILE_URL)

    assert result.video.bvid == "BV1qiKf65EW9"
    assert result.video.page_number == 1
