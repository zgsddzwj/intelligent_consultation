"""语义缓存系统 - 基于embedding相似度缓存LLM响应"""
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import json
from app.services.redis_service import redis_service
from app.services.milvus_service import get_milvus_service
from app.knowledge.rag.embedder import Embedder
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class SemanticCache:
    """语义缓存 - 基于embedding相似度"""
    
    def __init__(self):
        self.embedder = Embedder()
        self.similarity_threshold = settings.LLM_SEMANTIC_CACHE_THRESHOLD
        self.cache_collection_name = "llm_semantic_cache"
        self._init_cache_collection()
    
    def _init_cache_collection(self):
        """初始化缓存集合"""
        try:
            milvus_service = get_milvus_service()
            if not milvus_service:
                app_logger.warning("Milvus服务不可用，语义缓存将使用Redis降级")
                return
            
            # 检查集合是否存在
            from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility
            
            if utility.has_collection(self.cache_collection_name):
                self.collection = Collection(self.cache_collection_name)
            else:
                # 创建集合
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="query_embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),  # Qwen embedding维度
                    FieldSchema(name="query_text", dtype=DataType.VARCHAR, max_length=1000),
                    FieldSchema(name="response", dtype=DataType.VARCHAR, max_length=10000),
                    FieldSchema(name="metadata", dtype=DataType.JSON),
                    FieldSchema(name="timestamp", dtype=DataType.INT64)
                ]
                schema = CollectionSchema(fields, "LLM语义缓存集合")
                self.collection = Collection(self.cache_collection_name, schema)
                
                # 创建索引
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                self.collection.create_index(
                    field_name="query_embedding",
                    index_params=index_params
                )
                app_logger.info(f"语义缓存集合已创建: {self.cache_collection_name}")
            
            self.collection.load()
            self.use_milvus = True
            
        except Exception as e:
            app_logger.warning(f"初始化Milvus语义缓存失败，将使用Redis降级: {e}")
            self.use_milvus = False
    
    def get(self, query: str, top_k: int = 1) -> Optional[Dict[str, Any]]:
        """
        从语义缓存中获取相似查询的响应
        
        Args:
            query: 查询文本
            top_k: 返回最相似的k个结果
        
        Returns:
            缓存结果，如果没有找到相似的结果则返回None
        """
        if not settings.LLM_SEMANTIC_CACHE_ENABLED:
            return None
        
        try:
            # 生成查询embedding
            query_embedding = self.embedder.embed(query)
            if not query_embedding:
                return None
            
            if self.use_milvus:
                return self._get_from_milvus(query_embedding, top_k)
            else:
                return self._get_from_redis(query, query_embedding, top_k)
                
        except Exception as e:
            app_logger.warning(f"语义缓存查询失败: {e}")
            return None
    
    def _get_from_milvus(self, query_embedding: List[float], top_k: int) -> Optional[Dict[str, Any]]:
        """从Milvus获取缓存"""
        try:
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            results = self.collection.search(
                data=[query_embedding],
                anns_field="query_embedding",
                param=search_params,
                limit=top_k,
                output_fields=["query_text", "response", "metadata", "timestamp"]
            )
            
            if results and len(results[0]) > 0:
                # 检查相似度
                hit = results[0][0]
                similarity = hit.score
                
                if similarity >= self.similarity_threshold:
                    app_logger.info(f"语义缓存命中，相似度: {similarity:.3f}")
                    return {
                        "response": hit.entity.get("response"),
                        "metadata": hit.entity.get("metadata", {}),
                        "similarity": similarity,
                        "query_text": hit.entity.get("query_text")
                    }
            
            return None
            
        except Exception as e:
            app_logger.warning(f"Milvus语义缓存查询失败: {e}")
            return None
    
    def _get_from_redis(self, query: str, query_embedding: List[float], top_k: int) -> Optional[Dict[str, Any]]:
        """从Redis获取缓存（降级方案）"""
        try:
            # 获取所有缓存键
            cache_keys = redis_service.client.keys("semantic_cache:*")
            
            best_match = None
            best_similarity = 0.0
            
            for key in cache_keys[:100]:  # 限制检查数量
                try:
                    cached_data = redis_service.get_json(key)
                    if not cached_data:
                        continue
                    
                    cached_embedding = cached_data.get("embedding")
                    if not cached_embedding:
                        continue
                    
                    # 计算余弦相似度
                    similarity = self._cosine_similarity(query_embedding, cached_embedding)
                    
                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_match = {
                            "response": cached_data.get("response"),
                            "metadata": cached_data.get("metadata", {}),
                            "similarity": similarity,
                            "query_text": cached_data.get("query_text")
                        }
                        
                except Exception as e:
                    continue
            
            if best_match:
                app_logger.info(f"Redis语义缓存命中，相似度: {best_similarity:.3f}")
                return best_match
            
            return None
            
        except Exception as e:
            app_logger.warning(f"Redis语义缓存查询失败: {e}")
            return None
    
    def set(self, query: str, response: str, metadata: Optional[Dict[str, Any]] = None):
        """
        将查询和响应存储到语义缓存
        
        Args:
            query: 查询文本
            response: LLM响应
            metadata: 元数据（如模型、参数等）
        """
        if not settings.LLM_SEMANTIC_CACHE_ENABLED:
            return
        
        try:
            # 生成查询embedding
            query_embedding = self.embedder.embed(query)
            if not query_embedding:
                return
            
            import time
            timestamp = int(time.time())
            
            if self.use_milvus:
                self._set_to_milvus(query, query_embedding, response, metadata, timestamp)
            else:
                self._set_to_redis(query, query_embedding, response, metadata, timestamp)
                
        except Exception as e:
            app_logger.warning(f"语义缓存存储失败: {e}")
    
    def _set_to_milvus(self, query: str, query_embedding: List[float], 
                       response: str, metadata: Dict[str, Any], timestamp: int):
        """存储到Milvus"""
        try:
            data = [{
                "query_embedding": query_embedding,
                "query_text": query[:1000],  # 限制长度
                "response": response[:10000],  # 限制长度
                "metadata": json.dumps(metadata or {}),
                "timestamp": timestamp
            }]
            
            self.collection.insert(data)
            self.collection.flush()
            app_logger.debug(f"语义缓存已存储到Milvus: {query[:50]}...")
            
        except Exception as e:
            app_logger.warning(f"Milvus语义缓存存储失败: {e}")
    
    def _set_to_redis(self, query: str, query_embedding: List[float],
                      response: str, metadata: Dict[str, Any], timestamp: int):
        """存储到Redis（降级方案）"""
        try:
            import hashlib
            # 使用query的hash作为key的一部分
            query_hash = hashlib.md5(query.encode()).hexdigest()
            cache_key = f"semantic_cache:{query_hash}"
            
            cache_data = {
                "query_text": query,
                "embedding": query_embedding,
                "response": response,
                "metadata": metadata or {},
                "timestamp": timestamp
            }
            
            # 设置较长的TTL（7天）
            redis_service.set_json(cache_key, cache_data, ttl=7 * 24 * 3600)
            app_logger.debug(f"语义缓存已存储到Redis: {query[:50]}...")
            
        except Exception as e:
            app_logger.warning(f"Redis语义缓存存储失败: {e}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            app_logger.warning(f"计算余弦相似度失败: {e}")
            return 0.0
    
    def clear(self, older_than_days: int = 30):
        """清理旧缓存"""
        try:
            import time
            cutoff_timestamp = int(time.time()) - (older_than_days * 24 * 3600)
            
            if self.use_milvus:
                # Milvus清理（需要根据timestamp过滤）
                # 这里简化处理，实际可以使用Milvus的delete功能
                app_logger.info("Milvus缓存清理功能待实现")
            else:
                # Redis清理
                cache_keys = redis_service.client.keys("semantic_cache:*")
                cleared = 0
                for key in cache_keys:
                    try:
                        cached_data = redis_service.get_json(key)
                        if cached_data and cached_data.get("timestamp", 0) < cutoff_timestamp:
                            redis_service.delete(key)
                            cleared += 1
                    except:
                        continue
                app_logger.info(f"清理了 {cleared} 个旧缓存项")
                
        except Exception as e:
            app_logger.warning(f"缓存清理失败: {e}")


# 全局实例
semantic_cache = SemanticCache()

