from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class FetchConfig(BaseModel):
    timeout_seconds: float = Field(default=15.0, gt=0)
    user_agent: str = (
        "Mozilla/5.0 (compatible; bili-subtitle-service/0.1; "
        "+https://github.com/Toukou-Yuu/bili-subtitle-service)"
    )
    proxy: str | None = None
    cookie: str | None = None
    cookie_file: Path | None = None

    @field_validator("proxy", "cookie", mode="before")
    @classmethod
    def blank_string_is_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class SummaryConfig(BaseModel):
    model: str | None = None
    reasoning_effort: str | None = None


class AppConfig(BaseModel):
    fetch: FetchConfig = Field(default_factory=FetchConfig)
    summary: SummaryConfig = Field(default_factory=SummaryConfig)
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

        if env.get("BILI_SUBTITLE_TIMEOUT_SECONDS"):
            fetch_update["timeout_seconds"] = float(env["BILI_SUBTITLE_TIMEOUT_SECONDS"])
        if env.get("BILI_SUBTITLE_USER_AGENT"):
            fetch_update["user_agent"] = env["BILI_SUBTITLE_USER_AGENT"]
        if "BILI_SUBTITLE_PROXY" in env:
            proxy = env["BILI_SUBTITLE_PROXY"].strip()
            fetch_update["proxy"] = proxy or None
        if env.get("BILI_SUBTITLE_COOKIE"):
            cookie = env["BILI_SUBTITLE_COOKIE"].strip()
            fetch_update["cookie"] = cookie or None
        if env.get("BILI_SUBTITLE_COOKIE_FILE"):
            fetch_update["cookie_file"] = Path(env["BILI_SUBTITLE_COOKIE_FILE"])
        if env.get("BILI_SUBTITLE_SUMMARY_MODEL"):
            summary_update["model"] = env["BILI_SUBTITLE_SUMMARY_MODEL"]
        if env.get("BILI_SUBTITLE_SUMMARY_REASONING_EFFORT"):
            summary_update["reasoning_effort"] = env["BILI_SUBTITLE_SUMMARY_REASONING_EFFORT"]
        if env.get("BILI_SUBTITLE_LOG_LEVEL"):
            update["log_level"] = env["BILI_SUBTITLE_LOG_LEVEL"]

        if fetch_update:
            update["fetch"] = self.fetch.model_copy(update=fetch_update)
        if summary_update:
            update["summary"] = self.summary.model_copy(update=summary_update)
        config = self.model_copy(update=update) if update else self
        return config.load_secret_files()

    def load_secret_files(self) -> AppConfig:
        if not self.fetch.cookie_file or self.fetch.cookie:
            return self
        if not self.fetch.cookie_file.exists():
            raise FileNotFoundError(
                f"BILI_SUBTITLE_COOKIE_FILE does not exist: {self.fetch.cookie_file}"
            )
        cookie = self.fetch.cookie_file.read_text(encoding="utf-8").strip()
        return self.model_copy(update={"fetch": self.fetch.model_copy(update={"cookie": cookie})})
