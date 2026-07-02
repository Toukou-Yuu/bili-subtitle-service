import pytest

from bili_subtitle_service.extractor import parse_bilibili_url


def test_parse_watchlater_url_reads_bvid_query_parameter() -> None:
    reference = parse_bilibili_url(
        "https://www.bilibili.com/list/watchlater?bvid=BV1qiKf65EW9&oid=116838981704609"
    )

    assert reference.bvid == "BV1qiKf65EW9"
    assert reference.page_number == 1


def test_parse_video_url_reads_path_bvid_and_page() -> None:
    reference = parse_bilibili_url("https://www.bilibili.com/video/BV1qiKf65EW9/?p=3")

    assert reference.bvid == "BV1qiKf65EW9"
    assert reference.page_number == 3


def test_parse_bilibili_url_rejects_invalid_page() -> None:
    with pytest.raises(ValueError, match="分P参数无效"):
        parse_bilibili_url("https://www.bilibili.com/video/BV1qiKf65EW9/?p=abc")
