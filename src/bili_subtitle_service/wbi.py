from __future__ import annotations

import hashlib
import time
from urllib.parse import urlencode

MIXIN_KEY_ENC_TAB = [
    46,
    47,
    18,
    2,
    53,
    8,
    23,
    32,
    15,
    50,
    10,
    31,
    58,
    3,
    45,
    35,
    27,
    43,
    5,
    49,
    33,
    9,
    42,
    19,
    29,
    28,
    14,
    39,
    12,
    38,
    41,
    13,
    37,
    48,
    7,
    16,
    24,
    55,
    40,
    61,
    26,
    17,
    0,
    1,
    60,
    51,
    30,
    4,
    22,
    25,
    54,
    21,
    56,
    59,
    6,
    63,
    57,
    62,
    11,
    36,
    20,
    34,
    44,
    52,
]
FILTER_CHARS = "!'()*"


def make_mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    if len(raw) < 64:
        raise ValueError("WBI img/sub keys are too short")
    return "".join(raw[index] for index in MIXIN_KEY_ENC_TAB)[:32]


def sign_wbi_params(
    params: dict[str, object],
    *,
    mixin_key: str,
    timestamp: int | None = None,
) -> dict[str, str]:
    signed = {key: _sanitize_value(value) for key, value in params.items()}
    signed["wts"] = str(timestamp or int(time.time()))
    query = urlencode(sorted(signed.items()))
    signed["w_rid"] = hashlib.md5(f"{query}{mixin_key}".encode()).hexdigest()
    return signed


def _sanitize_value(value: object) -> str:
    return "".join(char for char in str(value) if char not in FILTER_CHARS)
