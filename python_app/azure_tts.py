import asyncio
import logging
import re
from typing import Dict, List, Optional

import httpx


class AzureTTSError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message

from .config import get_settings
from .cost_tracker import CostTracker
from .text_utils import escape_ssml, split_text


logger = logging.getLogger(__name__)

VOICE_URL = "https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
TTS_URL = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


class AzureTTSClient:
    def __init__(self, cost_tracker: CostTracker | None = None) -> None:
        self.settings = get_settings()
        self._client = httpx.AsyncClient(timeout=15.0)
        self.cost_tracker = cost_tracker

    async def list_voices(self, locale: Optional[str] = None) -> List[Dict]:
        url = VOICE_URL.format(region=self.settings.azure_region)
        headers = self._auth_headers()
        response = await self._client.get(url, headers=headers)
        response.raise_for_status()
        voices = response.json()
        if locale:
            voices = [voice for voice in voices if voice.get("Locale", "").startswith(locale)]
        return voices

    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        style: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> bytes:
        """Synthesize and return the entire audio payload."""
        settings = self.settings
        voice_name = voice or settings.default_voice
        rate_value = rate or settings.default_rate
        pitch_value = pitch or settings.default_pitch
        style_value = style or settings.default_style
        format_value = output_format or settings.output_format

        rate_value = self._normalize_prosody(rate_value, settings.default_rate)
        pitch_value = self._normalize_prosody(pitch_value, settings.default_pitch)

        if len(text) > settings.max_text_length:
            raise ValueError(f"Text length exceeds limit of {settings.max_text_length}")

        parts = split_text(text, settings.segment_length)
        logger.info("Splitting text into %s segments", len(parts))
        total_chars = sum(len(part) for part in parts)

        audio_segments: List[bytes] = []
        for index, part in enumerate(parts, 1):
            logger.debug(
                "Synthesizing segment %s/%s (%s chars)", index, len(parts), len(part)
            )
            audio = await self._synthesize_single(
                part, voice_name, rate_value, pitch_value, style_value, format_value
            )
            audio_segments.append(audio)

        if len(audio_segments) == 1:
            self._record_usage(total_chars)
            return audio_segments[0]
        combined = b"".join(audio_segments)
        self._record_usage(total_chars)
        return combined

    async def synthesize_stream(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        style: Optional[str] = None,
        output_format: Optional[str] = None,
    ):
        """Return an async iterator that streams audio bytes."""
        settings = self.settings
        voice_name = voice or settings.default_voice
        rate_value = rate or settings.default_rate
        pitch_value = pitch or settings.default_pitch
        style_value = style or settings.default_style
        format_value = output_format or settings.output_format

        rate_value = self._normalize_prosody(rate_value, settings.default_rate)
        pitch_value = self._normalize_prosody(pitch_value, settings.default_pitch)

        if len(text) > settings.max_text_length:
            raise ValueError(f"Text length exceeds limit of {settings.max_text_length}")

        parts = split_text(text, settings.segment_length)
        logger.info("Streaming %s segments", len(parts))
        total_chars = sum(len(part) for part in parts)

        async def generator():
            try:
                for index, part in enumerate(parts, 1):
                    logger.debug(
                        "Streaming segment %s/%s (%s chars)", index, len(parts), len(part)
                    )
                    async for chunk in self._synthesize_single_stream(
                        part,
                        voice_name,
                        rate_value,
                        pitch_value,
                        style_value,
                        format_value,
                    ):
                        yield chunk
            finally:
                self._record_usage(total_chars)

        return generator()

    async def _synthesize_single(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str,
        style: str,
        output_format: str,
    ) -> bytes:
        ssml = self._build_ssml(text, voice, rate, pitch, style)
        url = TTS_URL.format(region=self.settings.azure_region)
        headers = {
            **self._auth_headers(),
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": output_format,
            "User-Agent": "python-azure-tts",
        }
        try:
            response = await self._client.post(
                url, headers=headers, content=ssml.encode("utf-8")
            )
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as exc:
            raise AzureTTSError(self._format_http_error(exc), exc.response.status_code)
        except httpx.TimeoutException as exc:
            raise AzureTTSError(str(exc), status_code=504)
        except httpx.HTTPError as exc:
            raise AzureTTSError(str(exc))

    async def _synthesize_single_stream(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str,
        style: str,
        output_format: str,
    ):
        ssml = self._build_ssml(text, voice, rate, pitch, style)
        url = TTS_URL.format(region=self.settings.azure_region)
        headers = {
            **self._auth_headers(),
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": output_format,
            "User-Agent": "python-azure-tts",
        }

        try:
            async with self._client.stream(
                "POST", url, headers=headers, content=ssml.encode("utf-8")
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except httpx.HTTPStatusError as exc:
            raise AzureTTSError(self._format_http_error(exc), exc.response.status_code)
        except httpx.TimeoutException as exc:
            raise AzureTTSError(str(exc), status_code=504)
        except httpx.HTTPError as exc:
            raise AzureTTSError(str(exc))

    def _build_ssml(self, text: str, voice: str, rate: str, pitch: str, style: str) -> str:
        escaped_text = escape_ssml(text)
        locale = "-".join(voice.split("-")[:2]) if "-" in voice else "en-US"
        return (
            "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
            "xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='{locale}'>"
            "<voice name='{voice}'>"
            "<mstts:express-as style='{style}'>"
            "<prosody rate='{rate}' pitch='{pitch}'>"
            "{text}"
            "</prosody>"
            "</mstts:express-as>"
            "</voice>"
            "</speak>"
        ).format(
            locale=locale,
            voice=voice,
            style=style,
            rate=rate,
            pitch=pitch,
            text=escaped_text,
        )

    @staticmethod
    def _normalize_prosody(value: Optional[str], default: str) -> str:
        """Ensure rate/pitch values conform to SSML expectations.

        Azure expects a signed percentage (e.g., +0%, -5%). If callers supply a
        bare integer or float, we coerce it into that format. Any invalid value
        falls back to the configured default to avoid SSML parsing errors.
        """

        if value is None:
            return default

        trimmed = str(value).strip()
        if not trimmed:
            return default

        if trimmed.endswith("%"):
            return trimmed

        if re.match(r"^[+-]?\d+(?:\.\d+)?$", trimmed):
            if not trimmed.startswith(("+", "-")):
                trimmed = f"+{trimmed}"
            return f"{trimmed}%"

        logger.warning("Invalid prosody value '%s'; using default '%s'", trimmed, default)
        return default

    @staticmethod
    def _format_http_error(exc: httpx.HTTPStatusError) -> str:
        status = exc.response.status_code if exc.response else "unknown"
        detail = exc.response.text if exc.response else str(exc)
        return f"Azure TTS error {status}: {detail}"

    def _record_usage(self, char_count: int) -> None:
        if not self.cost_tracker or char_count <= 0:
            return
        try:
            self.cost_tracker.record(char_count)
        except Exception:  # pragma: no cover - I/O failures should not break synthesis
            logger.warning("Failed to record cost usage", exc_info=True)

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Ocp-Apim-Subscription-Key": self.settings.azure_key,
            "Ocp-Apim-Subscription-Region": self.settings.azure_region,
        }

    async def close(self) -> None:
        await self._client.aclose()


async def warmup(client: AzureTTSClient) -> None:
    try:
        await client.list_voices()
    except Exception as exc:  # pragma: no cover - warmup is best-effort
        logger.warning("Voice warmup failed: %s", exc)


def run_warmup(client: AzureTTSClient) -> None:
    asyncio.create_task(warmup(client))
