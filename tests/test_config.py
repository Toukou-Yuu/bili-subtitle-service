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


def test_raw_cookie_file_value_is_treated_as_sessdata(monkeypatch, tmp_path: Path) -> None:
    cookie_file = tmp_path / "bili-cookie.txt"
    cookie_file.write_text("raw-sessdata-value\n", encoding="utf-8")
    monkeypatch.setenv("BILI_SUBTITLE_COOKIE_FILE", str(cookie_file))

    config = AppConfig.from_env()

    assert config.fetch.cookie == "SESSDATA=raw-sessdata-value"


def test_raw_cookie_environment_value_is_treated_as_sessdata(monkeypatch) -> None:
    monkeypatch.setenv("BILI_SUBTITLE_COOKIE", "raw-sessdata-value")

    config = AppConfig.from_env()

    assert config.fetch.cookie == "SESSDATA=raw-sessdata-value"


def test_storage_and_retrieval_config_load_from_yaml_and_env(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "service.yaml"
    config_file.write_text(
        "storage:\n"
        "  enabled: true\n"
        "  library_dir: /data/library\n"
        "retrieval:\n"
        "  enabled: true\n"
        "  base_url: http://retrieval-api:8000/v1\n"
        "  collection: bili_video_notes\n"
        "  sync_by_default: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BILI_SUBTITLE_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("BILI_SUBTITLE_LIBRARY_DIR", str(tmp_path / "override-library"))
    monkeypatch.setenv("BILI_SUBTITLE_RETRIEVAL_COLLECTION", "bili_video_notes_dev")

    config = AppConfig.from_env()

    assert config.storage.enabled is True
    assert config.storage.library_dir == tmp_path / "override-library"
    assert config.retrieval.enabled is True
    assert config.retrieval.base_url == "http://retrieval-api:8000/v1"
    assert config.retrieval.collection == "bili_video_notes_dev"
    assert config.retrieval.sync_by_default is True
