import logging
import os
import sys
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .azure_tts import AzureTTSClient, warmup
from .auth import require_api_key
from .config import get_settings

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Azure TTS Service", version="1.0.0")
client = AzureTTSClient()


@app.on_event("startup")
async def _startup() -> None:  # pragma: no cover - framework hook
    await warmup(client)


@app.on_event("shutdown")
async def _shutdown() -> None:  # pragma: no cover - framework hook
    await client.close()


@app.get("/api/v1/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/api/v1/voices")
async def voices(
    locale: Optional[str] = Query(default=None, description="Locale filter, e.g. en-US"),
    authorization: Optional[str] = Header(default=None),
    api_key: Optional[str] = Query(default=None, alias="api_key"),
):
    settings = get_settings()
    require_api_key(settings.api_key, authorization, api_key)
    voices = await client.list_voices(locale)
    return voices


@app.get("/api/v1/tts")
async def tts_get(
    text: Optional[str] = Query(default=None),
    t: Optional[str] = Query(default=None, alias="t"),
    voice: Optional[str] = Query(default=None),
    v: Optional[str] = Query(default=None, alias="v"),
    rate: Optional[str] = Query(default=None),
    r: Optional[str] = Query(default=None, alias="r"),
    pitch: Optional[str] = Query(default=None),
    p: Optional[str] = Query(default=None, alias="p"),
    style: Optional[str] = Query(default=None),
    s: Optional[str] = Query(default=None, alias="s"),
    output_format: Optional[str] = Query(default=None),
    f: Optional[str] = Query(default=None, alias="f"),
    stream: Optional[bool] = Query(
        default=None,
        alias="stream",
        description="Whether to stream audio chunks back to the client",
    ),
    authorization: Optional[str] = Header(default=None),
    api_key: Optional[str] = Query(default=None, alias="api_key"),
):
    resolved_text = text or t
    if not resolved_text:
        raise HTTPException(status_code=400, detail="text is required")

    return await _speak(
        resolved_text,
        voice or v,
        rate or r,
        pitch or p,
        style or s,
        output_format or f,
        stream,
        authorization,
        api_key,
        None,
    )


@app.post("/api/v1/tts")
async def tts_post(
    payload: dict,
    authorization: Optional[str] = Header(default=None),
    api_key: Optional[str] = Query(default=None, alias="api_key"),
):
    text = payload.get("text") or payload.get("t")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    stream = _parse_bool(payload.get("stream"))
    return await _speak(
        text,
        payload.get("voice") or payload.get("v"),
        payload.get("rate") or payload.get("r"),
        payload.get("pitch") or payload.get("p"),
        payload.get("style") or payload.get("s"),
        payload.get("format") or payload.get("f"),
        stream,
        authorization,
        api_key,
        payload.get("api_key"),
    )


async def _speak(
    text: str,
    voice: Optional[str],
    rate: Optional[str],
    pitch: Optional[str],
    style: Optional[str],
    output_format: Optional[str],
    stream: Optional[bool],
    authorization: Optional[str],
    query_api_key: Optional[str],
    body_api_key: Optional[str],
):
    settings = get_settings()
    require_api_key(settings.api_key, authorization, query_api_key, body_api_key)
    use_streaming = stream if stream is not None else settings.enable_streaming
    try:
        if use_streaming:
            audio_iter = await client.synthesize_stream(
                text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                style=style,
                output_format=output_format,
            )
        else:
            audio = await client.synthesize(
                text,
                voice=voice,
                rate=rate,
                pitch=pitch,
                style=style,
                output_format=output_format,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=502, detail=str(exc))

    content_type = "audio/mpeg"
    if use_streaming:
        return StreamingResponse(audio_iter, media_type=content_type)
    return Response(content=audio, media_type=content_type)


@app.get("/api/v1/config")
async def config_endpoint():
    settings = get_settings()
    return {
        "default_voice": settings.default_voice,
        "default_style": settings.default_style,
        "default_rate": settings.default_rate,
        "default_pitch": settings.default_pitch,
        "output_format": settings.output_format,
        "max_text_length": settings.max_text_length,
        "segment_length": settings.segment_length,
        "enable_streaming": settings.enable_streaming,
        "region": settings.azure_region,
    }


def _parse_bool(value) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "t", "yes", "y", "on"}
    return None
