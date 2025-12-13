import pytest

from . import azure_tts
from .azure_tts import AzureTTSError, AzureTTSClient


@pytest.mark.parametrize(
    "value,default,expected",
    [
        (None, "+0%", "+0%"),
        ("", "+0%", "+0%"),
        ("+5%", "+0%", "+5%"),
        ("-3%", "+0%", "-3%"),
        ("10", "+0%", "+10%"),
        ("-1.5", "+0%", "-1.5%"),
        ("0", "+2%", "+0%"),
    ],
)
def test_normalize_prosody_valid_numbers(value, default, expected):
    assert AzureTTSClient._normalize_prosody(value, default) == expected


def test_normalize_prosody_invalid_falls_back_default(caplog):
    caplog.set_level("WARNING")
    result = AzureTTSClient._normalize_prosody("fast", "+1%")
    assert result == "+1%"
    assert "Invalid prosody value" in caplog.text


class _DummySettings:
    azure_key = "key"
    azure_region = "region"
    default_voice = "en-US-TestVoice"
    default_rate = "+0%"
    default_pitch = "+0%"
    default_style = "general"
    output_format = "audio-24khz-160kbitrate-mono-mp3"
    max_text_length = 100
    segment_length = 50


class _HTTPStatusStream:
    def __init__(self, status: int):
        self._status = status

    async def __aenter__(self):
        response = azure_tts.httpx.Response(
            self._status, request=azure_tts.httpx.Request("POST", "https://example.com")
        )
        raise azure_tts.httpx.HTTPStatusError(
            "boom", request=response.request, response=response
        )

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _TimeoutStream:
    async def __aenter__(self):
        raise azure_tts.httpx.ReadTimeout("timeout")

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeClient:
    def __init__(self, stream_obj):
        self._stream_obj = stream_obj

    def stream(self, *_args, **_kwargs):
        return self._stream_obj


@pytest.mark.anyio
async def test_stream_maps_http_status_error(monkeypatch):
    monkeypatch.setattr(azure_tts, "get_settings", lambda: _DummySettings())
    client = AzureTTSClient()
    client._client = _FakeClient(_HTTPStatusStream(503))

    with pytest.raises(AzureTTSError) as exc_info:
        async for _ in client._synthesize_single_stream("hi", "v", "+0%", "+0%", "s", "f"):
            pass

    assert exc_info.value.status_code == 503
    assert "Azure TTS error 503" in exc_info.value.message


@pytest.mark.anyio
async def test_stream_maps_timeout(monkeypatch):
    monkeypatch.setattr(azure_tts, "get_settings", lambda: _DummySettings())
    client = AzureTTSClient()
    client._client = _FakeClient(_TimeoutStream())

    with pytest.raises(AzureTTSError) as exc_info:
        async for _ in client._synthesize_single_stream("hi", "v", "+0%", "+0%", "s", "f"):
            pass

    assert exc_info.value.status_code == 504
    assert "timeout" in exc_info.value.message
