"""认证中间件单元测试"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.middleware.auth import AuthMiddleware
from app.common.exceptions import ErrorCode
from app.utils.security import create_access_token


def _make_request(path: str, authorization: str | None = None):
    request = MagicMock()
    request.url.path = path
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization
    request.headers.get.side_effect = lambda key, default=None: headers.get(key, default)
    return request


@pytest.mark.asyncio
async def test_public_paths_skip_auth():
    middleware = AuthMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    for path in ("/health", "/live", "/api/v1/users/login", "/api/v1/users/register"):
        request = _make_request(path)
        await middleware.dispatch(request, call_next)
        call_next.assert_called_once()
        call_next.reset_mock()


@pytest.mark.asyncio
async def test_missing_token_returns_401():
    middleware = AuthMiddleware(app=MagicMock())
    request = _make_request("/api/v1/consultation/chat")
    call_next = AsyncMock()

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["error"]["code"] == ErrorCode.UNAUTHORIZED
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_token_returns_401():
    middleware = AuthMiddleware(app=MagicMock())
    request = _make_request("/api/v1/consultation/chat", "Bearer invalid.token")
    call_next = AsyncMock()

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    body = json.loads(response.body)
    assert body["error"]["code"] == ErrorCode.TOKEN_INVALID
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_valid_token_passes_through():
    middleware = AuthMiddleware(app=MagicMock())
    token = create_access_token({"sub": "42", "role": "patient"})
    request = _make_request("/api/v1/consultation/chat", f"Bearer {token}")
    expected = MagicMock(status_code=200)
    call_next = AsyncMock(return_value=expected)

    response = await middleware.dispatch(request, call_next)

    assert response is expected
    assert request.state.user_id == "42"
    assert request.state.user_role == "patient"
    call_next.assert_called_once()
