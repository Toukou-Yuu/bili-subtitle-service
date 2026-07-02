from bili_subtitle_service.text import clean_subtitle_text


def test_clean_subtitle_text_removes_standalone_fillers_and_joins_punctuation() -> None:
    cleaned = clean_subtitle_text(
        [
            "啊",
            "这个 方法会改变你看到的内容",
            "重点是个性化推荐",
            "，不是你真的自由选择",
            "嗯",
        ]
    )

    assert cleaned == "方法会改变你看到的内容\n重点是个性化推荐，不是你真的自由选择"


def test_clean_subtitle_text_preserves_meaningful_words_inside_sentences() -> None:
    cleaned = clean_subtitle_text(["然后性原理不是这里的重点", "这就是控制感的来源"])

    assert "然后性原理" in cleaned
    assert "这就是控制感" in cleaned
