from __future__ import annotations

import re

FILLER_WORDS = (
    "啊",
    "嗯",
    "呃",
    "额",
    "那个啥",
    "那个",
    "然后",
    "就是说",
    "就是",
    "这个",
    "你知道吧",
)
_DELIMITERS = "，。！？；、,\\s"
_FILLER_RE = re.compile(
    rf"(^|[{_DELIMITERS}])(?:{'|'.join(map(re.escape, FILLER_WORDS))})(?=$|[{_DELIMITERS}])"
)


def clean_subtitle_text(text_items: list[str]) -> str:
    text = "\n".join(item.strip() for item in text_items if item and item.strip())

    previous = None
    while previous != text:
        previous = text
        text = _FILLER_RE.sub(r"\1", text)

    return normalize_cleaned_text(text)


def normalize_cleaned_text(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("\n ", "\n").replace(" \n", "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[，,]{2,}", "，", text)
    text = re.sub(r"。{2,}", "。", text)
    text = re.sub(r"\n([，。！？；、])", r"\1", text)
    text = re.sub(r"([，。！？；、])\n", r"\1", text)
    return text.strip()
