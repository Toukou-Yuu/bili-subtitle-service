from pathlib import Path

from bili_subtitle_service.config import AppConfig


def test_config_file_loads_summary_defaults_without_hardcoding_model(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "service.yaml"
    config_file.write_text(
        "summary:\n"
        "  model: deepseek-v4-flash\n"
        "  reasoning_effort: high\n"
        "fetch:\n"
        "  timeout_seconds: 9\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BILI_SUBTITLE_CONFIG_FILE", str(config_file))

    config = AppConfig.from_env()

    assert config.summary.model == "deepseek-v4-flash"
    assert config.summary.reasoning_effort == "high"
    assert config.fetch.timeout_seconds == 9


def test_environment_overrides_config_file(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "service.yaml"
    config_file.write_text("summary:\n  model: other-model\n", encoding="utf-8")
    monkeypatch.setenv("BILI_SUBTITLE_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("BILI_SUBTITLE_SUMMARY_MODEL", "deepseek-v4-flash")

    config = AppConfig.from_env()

    assert config.summary.model == "deepseek-v4-flash"


def test_cookie_can_be_loaded_from_secret_file(monkeypatch, tmp_path: Path) -> None:
    cookie_file = tmp_path / "bili-cookie.txt"
    cookie_file.write_text("SESSDATA=secret-cookie\n", encoding="utf-8")
    monkeypatch.setenv("BILI_SUBTITLE_COOKIE_FILE", str(cookie_file))

    config = AppConfig.from_env()

    assert config.fetch.cookie == "SESSDATA=secret-cookie"


def test_blank_proxy_environment_override_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("BILI_SUBTITLE_PROXY", "")

    config = AppConfig.from_env()

    assert config.fetch.proxy is None
