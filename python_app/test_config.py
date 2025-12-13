import os

import pytest

from . import config as config_module
from .config import Settings


def test_settings_load_from_yaml(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
{
  "azure": {"key": "test-key", "region": "eastasia"},
  "auth": {"api_key": "client-key"},
  "cost": {"output_dir": "/tmp/costs", "price_per_million_chars": 20},
  "defaults": {
    "voice": "custom-voice",
    "style": "excited",
    "rate": "+20%",
    "pitch": "+2%",
    "output_format": "audio-16khz-32kbitrate-mono-mp3",
    "max_text_length": 999,
    "segment_length": 123,
    "enable_streaming": true
  },
  "telegram": {
    "enabled": true,
    "bot_token": "tg-token",
    "chat_id": "tg-chat",
    "daily_hour_utc": 6
  }
}
        """,
        encoding="utf-8",
    )

    # Reset cached settings and load from the temp file
    config_module.settings = None
    settings = Settings.from_file(cfg)

    assert settings.azure_key == "test-key"
    assert settings.azure_region == "eastasia"
    assert settings.api_key == "client-key"
    assert settings.default_voice == "custom-voice"
    assert settings.default_style == "excited"
    assert settings.default_rate == "+20%"
    assert settings.default_pitch == "+2%"
    assert settings.output_format == "audio-16khz-32kbitrate-mono-mp3"
    assert settings.max_text_length == 999
    assert settings.segment_length == 123
    assert settings.enable_streaming is True
    assert settings.cost_output_dir == "/tmp/costs"
    assert settings.price_per_million_chars == 20.0
    assert settings.telegram_enabled is True
    assert settings.telegram_bot_token == "tg-token"
    assert settings.telegram_chat_id == "tg-chat"
    assert settings.telegram_daily_hour_utc == 6


def test_env_override_for_secrets(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
{
  "azure": {"key": "file-key", "region": "file-region"},
  "auth": {},
  "cost": {"price_per_million_chars": 50}
}
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("AZURE_TTS_KEY", "env-key")
    monkeypatch.setenv("AZURE_TTS_REGION", "env-region")
    monkeypatch.setenv("COST_OUTPUT_DIR", "/data/costs")
    monkeypatch.setenv("PRICE_PER_MILLION_CHARS", "25.5")
    monkeypatch.setenv("TELEGRAM_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "env-chat")
    monkeypatch.setenv("TELEGRAM_DAILY_HOUR_UTC", "12")
    config_module.settings = None

    settings = Settings.from_file(cfg)

    assert settings.azure_key == "env-key"
    assert settings.azure_region == "env-region"
    assert settings.cost_output_dir == "/data/costs"
    assert settings.price_per_million_chars == 25.5
    assert settings.telegram_enabled is True
    assert settings.telegram_bot_token == "env-token"
    assert settings.telegram_chat_id == "env-chat"
    assert settings.telegram_daily_hour_utc == 12
