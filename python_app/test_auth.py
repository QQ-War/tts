import pytest

try:  # pragma: no cover - optional dependency for CI environments without FastAPI
    from fastapi import HTTPException
except ImportError:  # pragma: no cover - skip tests if dependency unavailable
    pytest.skip("fastapi not installed", allow_module_level=True)

from .auth import pick_api_key, require_api_key


def test_pick_api_key_priority_order():
    assert pick_api_key("Bearer headerKey", "query", "body") == "headerKey"
    assert pick_api_key(None, "query", "body") == "query"
    assert pick_api_key(None, None, "body") == "body"
    assert pick_api_key("   ", None, None) is None


def test_require_api_key_allows_match_any_location():
    require_api_key("secret", "Bearer secret", None)
    require_api_key("secret", "secret", None)
    require_api_key("secret", None, "secret")
    require_api_key("secret", None, None, "secret")


@pytest.mark.parametrize(
    "auth,query,body",
    [
        (None, None, None),
        ("Bearer wrong", None, None),
        (None, "wrong", None),
        (None, None, "wrong"),
    ],
)
def test_require_api_key_rejects_invalid(auth, query, body):
    with pytest.raises(HTTPException) as excinfo:
        require_api_key("secret", auth, query, body)
    assert excinfo.value.status_code == 401
