from bili_subtitle_service.wbi import make_mixin_key, sign_wbi_params


def test_make_mixin_key_uses_bilibili_permutation() -> None:
    raw = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/"

    assert make_mixin_key(raw[:32], raw[32:]) == "UVsc1ixGpYkF6dTJBRfXHjQtDCoNmMPn"


def test_sign_wbi_params_sorts_filters_and_adds_md5_signature() -> None:
    signed = sign_wbi_params(
        {"cid": "321", "aid": "123", "unsafe": "a!'()*b"},
        mixin_key="UVsc1ixGpYkF6dTJBRfXHjQtDCoNmMPn",
        timestamp=1700000000,
    )

    assert signed == {
        "aid": "123",
        "cid": "321",
        "unsafe": "ab",
        "wts": "1700000000",
        "w_rid": "1e433306ba3ece4a1cf24f7347f5fba1",
    }
