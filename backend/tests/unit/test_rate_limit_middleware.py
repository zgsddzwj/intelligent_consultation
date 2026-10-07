"""限流中间件客户端标识与内网判定测试"""

from types import SimpleNamespace

from app.api.middleware.rate_limit_enhanced import (
    RateLimitEnhancedMiddleware,
    _is_internal_peer,
)


def _request(client_host, headers=None):
    return SimpleNamespace(
        client=SimpleNamespace(host=client_host) if client_host else None,
        state=SimpleNamespace(),
        headers=headers or {},
    )


def _middleware():
    return RateLimitEnhancedMiddleware(app=None)


def test_internal_peer_detection():
    """内网/回环地址判定：Docker/K8s 网段与回环为内网，公网不是"""
    assert _is_internal_peer("172.18.0.5")
    assert _is_internal_peer("10.1.2.3")
    assert _is_internal_peer("192.168.1.10")
    assert _is_internal_peer("127.0.0.1")
    assert not _is_internal_peer("8.8.8.8")
    assert not _is_internal_peer("not-an-ip")
    assert not _is_internal_peer("")


def test_public_client_ignores_forwarded_headers():
    """公网直连客户端：不信任 X-Forwarded-For / X-Real-IP（防伪造绕过限流）"""
    mw = _middleware()
    request = _request(
        "8.8.8.8",
        {"X-Forwarded-For": "6.6.6.6", "X-Real-IP": "1.2.3.4"},
    )
    assert mw._get_client_key(request) == "ratelimit:ip:8.8.8.8"


def test_internal_peer_trusts_overwritten_real_ip():
    """内网反代（nginx 以 $remote_addr 覆写 X-Real-IP）→ 信任 X-Real-IP"""
    mw = _middleware()
    request = _request("172.18.0.5", {"X-Real-IP": "203.0.113.7"})
    assert mw._get_client_key(request) == "ratelimit:ip:203.0.113.7"


def test_internal_peer_without_real_ip_falls_back():
    """内网直连但无 X-Real-IP → 回退直连地址"""
    mw = _middleware()
    request = _request("172.18.0.5")
    assert mw._get_client_key(request) == "ratelimit:ip:172.18.0.5"


def test_user_id_takes_precedence():
    """已认证用户优先按用户ID限流"""
    mw = _middleware()
    request = SimpleNamespace(
        client=SimpleNamespace(host="8.8.8.8"),
        state=SimpleNamespace(user_id="u-123"),
        headers={},
    )
    assert mw._get_client_key(request) == "ratelimit:user:u-123"
