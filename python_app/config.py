import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:  # PyYAML may not be available in restricted environments
    import yaml
except ImportError:  # pragma: no cover - fallback path exercised in tests
    yaml = None


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
CONFIG_PATH_ENV = "TTS_CONFIG_PATH"


@dataclass
class Settings:
    azure_key: str
    azure_region: str
    api_key: str = ""
    cost_output_dir: str = "/app/cost"
    price_per_million_chars: float = 15.0
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_daily_hour_utc: int = 9
    default_voice: str = "zh-CN-XiaoxiaoNeural"
    default_style: str = "general"
    default_rate: str = "+0%"
    default_pitch: str = "+0%"
    output_format: str = "audio-24khz-160kbitrate-mono-mp3"
    max_text_length: int = 4500
    segment_length: int = 300
    enable_streaming: bool = False

    @classmethod
    def from_file(cls, path: Optional[str] = None) -> "Settings":
        config_path = Path(path or os.getenv(CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH))
        if not config_path.is_file():
            raise RuntimeError(f"Config file not found at {config_path}")

        data = _load_yaml(config_path)
        azure_cfg = data.get("azure", {})
        defaults = data.get("defaults", {})
        auth_cfg = data.get("auth", {})
        cost_cfg = data.get("cost", {})
        telegram_cfg = data.get("telegram", {})

        azure_key = os.getenv("AZURE_TTS_KEY") or azure_cfg.get("key")
        azure_region = os.getenv("AZURE_TTS_REGION") or azure_cfg.get("region")
        if not azure_key or not azure_region:
            raise RuntimeError("Azure Speech key/region must be provided in config.yaml or environment")

        return cls(
            azure_key=azure_key,
            azure_region=azure_region,
            api_key=os.getenv("TTS_API_KEY", auth_cfg.get("api_key", cls.api_key)),
            default_voice=defaults.get("voice", cls.default_voice),
            default_style=defaults.get("style", cls.default_style),
            default_rate=defaults.get("rate", cls.default_rate),
            default_pitch=defaults.get("pitch", cls.default_pitch),
            output_format=defaults.get("output_format", cls.output_format),
            max_text_length=int(defaults.get("max_text_length", cls.max_text_length)),
            segment_length=int(defaults.get("segment_length", cls.segment_length)),
            enable_streaming=_coerce_bool(defaults.get("enable_streaming", cls.enable_streaming)),
            cost_output_dir=os.getenv("COST_OUTPUT_DIR", cost_cfg.get("output_dir", cls.cost_output_dir)),
            price_per_million_chars=_coerce_float(
                os.getenv("PRICE_PER_MILLION_CHARS", cost_cfg.get("price_per_million_chars", cls.price_per_million_chars)),
                cls.price_per_million_chars,
            ),
            telegram_enabled=_coerce_bool(
                os.getenv(
                    "TELEGRAM_NOTIFICATIONS_ENABLED",
                    telegram_cfg.get("enabled", cls.telegram_enabled),
                )
            ),
            telegram_bot_token=os.getenv(
                "TELEGRAM_BOT_TOKEN", telegram_cfg.get("bot_token", cls.telegram_bot_token)
            ),
            telegram_chat_id=os.getenv(
                "TELEGRAM_CHAT_ID", telegram_cfg.get("chat_id", cls.telegram_chat_id)
            ),
            telegram_daily_hour_utc=int(
                os.getenv(
                    "TELEGRAM_DAILY_HOUR_UTC",
                    telegram_cfg.get("daily_hour_utc", cls.telegram_daily_hour_utc),
                )
            ),
        )


settings: Optional[Settings] = None


def get_settings() -> Settings:
    global settings
    if settings is None:
        settings = Settings.from_file()
    return settings


def _load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - guidance for missing deps
        raise RuntimeError(
            "PyYAML is not installed and config.yaml is not valid JSON. "
            "Install PyYAML or provide JSON-formatted config."
        ) from exc


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in {"1", "true", "t", "yes", "y", "on"}
    return False


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
