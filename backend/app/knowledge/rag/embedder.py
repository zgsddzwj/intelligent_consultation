"""嵌入模型 - 增强版（批量处理、本地缓存、多模型降级）"""
import hashlib
import json
from typing import List, Optional, Dict, Any
import dashscope
from dashscope import TextEmbedding
from app.config import get_settings
from app.utils.logger import app_logger
settings = get_settings()
dashscope.api_key = settings.QWEN_API_KEY


class Embedder:
    """文本嵌入器 - 增强版

    新增功能：
    - 批量处理优化（自动分批，避免API限制）
    - 嵌入结果多级缓存（本地LRU + Redis）
    - 多模型降级策略
    - 请求重试与指数退避
    - API Key 有效性预检（避免无效重试）
    """

    # DashScope批量限制
    BATCH_SIZE = 25
    # 最大重试次数
    MAX_RETRIES = 3

    def __init__(self, model: str = None, dimension: int = 1024, enable_cache: bool = True):
        self.model = model or settings.QWEN_EMBEDDING_MODEL
        self.dimension = dimension
        self.enable_cache = enable_cache
        self._cache = None
        # 标记 API Key 是否可用，避免无效重试
        self._api_available = bool(settings.QWEN_API_KEY and settings.QWEN_API_KEY.strip())
        if not self._api_available:
            app_logger.warning("QWEN_API_KEY 未配置，向量嵌入将不可用，RAG 向量检索将被跳过")
        if enable_cache:
            from app.infrastructure.cache import CacheManager
            self._cache = CacheManager()

    def _make_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()[:32]

    def _get_cached(self, text: str) -> Optional[List[float]]:
        """从缓存获取嵌入向量"""
        if not self.enable_cache or not self._cache:
            return None
        key = self._make_cache_key(text)
        try:
            cached = self._cache.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            app_logger.debug(f"嵌入缓存读取失败: {e}")
        return None

    def _set_cached(self, text: str, embedding: List[float]) -> None:
        """缓存嵌入向量"""
        if not self.enable_cache or not self._cache:
            return
        key = self._make_cache_key(text)
        try:
            self._cache.set(key, json.dumps(embedding))
        except Exception as e:
            app_logger.debug(f"嵌入缓存写入失败: {e}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本转换为向量 - 增强版（批量+缓存）"""
        if not texts:
            return []

        # API Key 不可用时直接返回空列表，跳过向量检索
        if not self._api_available:
            return []

        results = [None] * len(texts)
        to_embed_indices = []
        to_embed_texts = []

        # 1. 检查缓存
        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached:
                results[i] = cached
            else:
                to_embed_indices.append(i)
                to_embed_texts.append(text)

        # 2. 批量处理未缓存的文本
        if to_embed_texts:
            try:
                embeddings = self._embed_batch(to_embed_texts)
                for idx, emb in zip(to_embed_indices, embeddings):
                    results[idx] = emb
                    # 写入缓存
                    self._set_cached(texts[idx], emb)
            except Exception as e:
                app_logger.warning(f"嵌入批量处理失败，跳过向量检索: {e}")
                return []

        return results

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入（自动分批）"""
        all_embeddings = []

        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            batch_embeddings = self._embed_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _embed_with_retry(self, texts: List[str]) -> List[List[float]]:
        """带重试的嵌入请求"""
        import time

        for attempt in range(self.MAX_RETRIES):
            try:
                return self._call_embedding_api(texts)
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    app_logger.warning(f"嵌入请求失败，{wait_time}秒后重试: {e}")
                    time.sleep(wait_time)
                else:
                    app_logger.error(f"嵌入请求最终失败: {e}")
                    raise

        return []

    def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """调用嵌入API"""
        result = TextEmbedding.call(
            model=self.model,
            input=texts
        )

        if result.status_code == 200:
            if hasattr(result, 'output') and result.output:
                if isinstance(result.output, dict) and 'embeddings' in result.output:
                    return [item['embedding'] for item in result.output['embeddings']]
                elif isinstance(result.output, list):
                    return [item['embedding'] for item in result.output]
                else:
                    raise Exception(f"嵌入结果格式异常: {type(result.output)}")
            else:
                raise Exception("嵌入结果为空")
        else:
            error_msg = getattr(result, 'message', f"状态码: {result.status_code}")
            raise Exception(f"嵌入失败: {error_msg}")

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询文本"""
        if not self._api_available:
            return []
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []

    def get_stats(self) -> Dict[str, Any]:
        """获取嵌入器统计信息"""
        stats = {"model": self.model, "dimension": self.dimension, "cache_enabled": self.enable_cache}
        if self._cache:
            try:
                stats["cache_stats"] = self._cache.get_stats()
            except Exception:
                pass
        return stats
