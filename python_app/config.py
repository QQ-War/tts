import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    azure_key: str
    azure_region: str
    api_key: str = ""
    default_voice: str = "zh-CN-XiaoxiaoNeural"
    default_style: str = "general"
    default_rate: str = "+0%"
    default_pitch: str = "+0%"
    output_format: str = "audio-24khz-160kbitrate-mono-mp3"
    max_text_length: int = 4500
    segment_length: int = 300
    enable_streaming: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("AZURE_TTS_KEY")
        region = os.getenv("AZURE_TTS_REGION")
        if not key or not region:
            raise RuntimeError("AZURE_TTS_KEY and AZURE_TTS_REGION must be set")

        return cls(
            azure_key=key,
            azure_region=region,
            api_key=os.getenv("TTS_API_KEY", cls.api_key),
            default_voice=os.getenv("TTS_DEFAULT_VOICE", cls.default_voice),
            default_style=os.getenv("TTS_DEFAULT_STYLE", cls.default_style),
            default_rate=os.getenv("TTS_DEFAULT_RATE", cls.default_rate),
            default_pitch=os.getenv("TTS_DEFAULT_PITCH", cls.default_pitch),
            output_format=os.getenv("TTS_OUTPUT_FORMAT", cls.output_format),
            max_text_length=int(os.getenv("TTS_MAX_TEXT_LENGTH", cls.max_text_length)),
            segment_length=int(os.getenv("TTS_SEGMENT_LENGTH", cls.segment_length)),
            enable_streaming=_get_bool("TTS_ENABLE_STREAMING", cls.enable_streaming),
        )


settings: Optional[Settings] = None


def get_settings() -> Settings:
    global settings
    if settings is None:
        settings = Settings.from_env()
    return settings


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y", "on"}
