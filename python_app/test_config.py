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
  "defaults": {
    "voice": "custom-voice",
    "style": "excited",
    "rate": "+20%",
    "pitch": "+2%",
    "output_format": "audio-16khz-32kbitrate-mono-mp3",
    "max_text_length": 999,
    "segment_length": 123,
    "enable_streaming": true
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


def test_env_override_for_secrets(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
{
  "azure": {"key": "file-key", "region": "file-region"},
  "auth": {}
}
        """,
        encoding="utf-8",
    )

    monkeypatch.setenv("AZURE_TTS_KEY", "env-key")
    monkeypatch.setenv("AZURE_TTS_REGION", "env-region")
    config_module.settings = None

    settings = Settings.from_file(cfg)

    assert settings.azure_key == "env-key"
    assert settings.azure_region == "env-region"
