"""Embedder 客户端复用测试"""
from app.knowledge.rag.embedder import Embedder


def test_embedder_client_reused_across_instances(monkeypatch):
    """多个 Embedder 实例应共享同一个 OpenAI 客户端（复用连接池）"""
    created = []

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            created.append(self)

    old_client = Embedder._client
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    try:
        e1 = Embedder(enable_cache=False)
        e2 = Embedder(enable_cache=False)
        c1 = e1._get_client()
        c2 = e2._get_client()
        assert c1 is c2
        assert len(created) == 1
    finally:
        Embedder._client = old_client
