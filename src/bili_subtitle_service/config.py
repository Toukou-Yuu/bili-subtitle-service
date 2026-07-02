from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


def normalize_cookie_header(value: str | None) -> str | None:
    """Normalize Cookie config without requiring users to paste a full header.

    Browser exports usually contain a complete Cookie header such as
    ``SESSDATA=...; bili_jct=...``. Mobile/chat workflows often only have the
    SESSDATA value. Treat a bare value as SESSDATA while preserving complete
    cookie headers unchanged.
    """
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    if stripped.lower().startswith("cookie:"):
        stripped = stripped.split(":", 1)[1].strip()

    if "\n" in stripped or "\r" in stripped:
        parts = [part.strip().rstrip(";") for part in stripped.splitlines() if part.strip()]
        stripped = "; ".join(parts)

    if "=" not in stripped:
        return f"SESSDATA={stripped}"
    return stripped


class FetchConfig(BaseModel):
    timeout_seconds: float = Field(default=15.0, gt=0)
    user_agent: str = (
        "Mozilla/5.0 (compatible; bili-subtitle-service/0.1; "
        "+https://github.com/Toukou-Yuu/bili-subtitle-service)"
    )
    proxy: str | None = None
    cookie: str | None = None
    cookie_file: Path | None = None

    @field_validator("proxy", mode="before")
    @classmethod
    def blank_proxy_is_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("cookie", mode="before")
    @classmethod
    def normalize_cookie(cls, value: Any) -> Any:
        if isinstance(value, str):
            return normalize_cookie_header(value)
        return value


class SummaryConfig(BaseModel):
    model: str | None = None
    reasoning_effort: str | None = None


class StorageConfig(BaseModel):
    enabled: bool = True
    library_dir: Path = Path("/data/library")


class RetrievalConfig(BaseModel):
    enabled: bool = False
    base_url: str = "http://retrieval-api:8000/v1"
    collection: str = "bili_video_notes"
    sync_by_default: bool = False


class AppConfig(BaseModel):
    fetch: FetchConfig = Field(default_factory=FetchConfig)
    summary: SummaryConfig = Field(default_factory=SummaryConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> AppConfig:
        data: dict[str, Any] = {}
        config_file = os.getenv("BILI_SUBTITLE_CONFIG_FILE")
        if config_file:
            path = Path(config_file)
            if not path.exists():
                raise FileNotFoundError(f"BILI_SUBTITLE_CONFIG_FILE does not exist: {path}")
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ValueError("BILI_SUBTITLE_CONFIG_FILE must contain a YAML mapping")
            data = loaded

        config = cls.model_validate(data)
        return config.apply_env_overrides(os.environ)

    def apply_env_overrides(self, env: Mapping[str, str]) -> AppConfig:
        update: dict[str, Any] = {}
        fetch_update: dict[str, Any] = {}
        summary_update: dict[str, Any] = {}
        storage_update: dict[str, Any] = {}
        retrieval_update: dict[str, Any] = {}

        if env.get("BILI_SUBTITLE_TIMEOUT_SECONDS"):
            fetch_update["timeout_seconds"] = float(env["BILI_SUBTITLE_TIMEOUT_SECONDS"])
        if env.get("BILI_SUBTITLE_USER_AGENT"):
            fetch_update["user_agent"] = env["BILI_SUBTITLE_USER_AGENT"]
        if "BILI_SUBTITLE_PROXY" in env:
            proxy = env["BILI_SUBTITLE_PROXY"].strip()
            fetch_update["proxy"] = proxy or None
        if env.get("BILI_SUBTITLE_COOKIE"):
            fetch_update["cookie"] = normalize_cookie_header(env["BILI_SUBTITLE_COOKIE"])
        if env.get("BILI_SUBTITLE_COOKIE_FILE"):
            fetch_update["cookie_file"] = Path(env["BILI_SUBTITLE_COOKIE_FILE"])
        if env.get("BILI_SUBTITLE_SUMMARY_MODEL"):
            summary_update["model"] = env["BILI_SUBTITLE_SUMMARY_MODEL"]
        if env.get("BILI_SUBTITLE_SUMMARY_REASONING_EFFORT"):
            summary_update["reasoning_effort"] = env["BILI_SUBTITLE_SUMMARY_REASONING_EFFORT"]
        if env.get("BILI_SUBTITLE_STORAGE_ENABLED"):
            storage_update["enabled"] = _env_bool(env["BILI_SUBTITLE_STORAGE_ENABLED"])
        if env.get("BILI_SUBTITLE_LIBRARY_DIR"):
            storage_update["library_dir"] = Path(env["BILI_SUBTITLE_LIBRARY_DIR"])
        if env.get("BILI_SUBTITLE_RETRIEVAL_ENABLED"):
            retrieval_update["enabled"] = _env_bool(env["BILI_SUBTITLE_RETRIEVAL_ENABLED"])
        if env.get("BILI_SUBTITLE_RETRIEVAL_BASE_URL"):
            retrieval_update["base_url"] = env["BILI_SUBTITLE_RETRIEVAL_BASE_URL"].rstrip("/")
        if env.get("BILI_SUBTITLE_RETRIEVAL_COLLECTION"):
            retrieval_update["collection"] = env["BILI_SUBTITLE_RETRIEVAL_COLLECTION"]
        if env.get("BILI_SUBTITLE_RETRIEVAL_SYNC_BY_DEFAULT"):
            retrieval_update["sync_by_default"] = _env_bool(
                env["BILI_SUBTITLE_RETRIEVAL_SYNC_BY_DEFAULT"]
            )
        if env.get("BILI_SUBTITLE_LOG_LEVEL"):
            update["log_level"] = env["BILI_SUBTITLE_LOG_LEVEL"]

        if fetch_update:
            update["fetch"] = self.fetch.model_copy(update=fetch_update)
        if summary_update:
            update["summary"] = self.summary.model_copy(update=summary_update)
        if storage_update:
            update["storage"] = self.storage.model_copy(update=storage_update)
        if retrieval_update:
            update["retrieval"] = self.retrieval.model_copy(update=retrieval_update)
        config = self.model_copy(update=update) if update else self
        return config.load_secret_files()

    def load_secret_files(self) -> AppConfig:
        if not self.fetch.cookie_file or self.fetch.cookie:
            return self
        if not self.fetch.cookie_file.exists():
            raise FileNotFoundError(
                f"BILI_SUBTITLE_COOKIE_FILE does not exist: {self.fetch.cookie_file}"
            )
        cookie = normalize_cookie_header(self.fetch.cookie_file.read_text(encoding="utf-8"))
        return self.model_copy(update={"fetch": self.fetch.model_copy(update={"cookie": cookie})})


def _env_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean environment value: {value}")
