from typing import Optional

from fastapi import HTTPException


def _normalize_auth_header(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    if stripped.lower().startswith("bearer "):
        stripped = stripped[7:].strip()
    return stripped or None


def pick_api_key(
    auth_header: Optional[str],
    query_key: Optional[str],
    body_key: Optional[str] = None,
) -> Optional[str]:
    """Return the first non-empty api key with header > query > body priority."""
    for candidate in (_normalize_auth_header(auth_header), query_key, body_key):
        if candidate:
            return candidate
    return None


def require_api_key(
    expected: str,
    auth_header: Optional[str],
    query_key: Optional[str],
    body_key: Optional[str] = None,
) -> None:
    """Validate that the provided key matches the expected one."""
    if not expected:
        return

    provided = pick_api_key(auth_header, query_key, body_key)
    if not provided:
        raise HTTPException(status_code=401, detail="未提供授权令牌")

    if provided != expected:
        raise HTTPException(status_code=401, detail="未授权访问: 无效的 API 密钥")
