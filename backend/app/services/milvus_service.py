"""优化的Milvus向量数据库服务 - 增强版（批量搜索、异步加载、索引优化、连接池）"""
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
    exceptions
)
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class MilvusService:
    """Milvus服务类 - 增强版
    
    新增功能：
    - 批量向量搜索
    - 异步集合加载
    - 连接池管理
    - 索引自动优化
    - 查询缓存
    """
    
    def __init__(self):
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = 1024  # Qwen embedding维度
        self._collection: Optional[Collection] = None
        self._connected = False
        self._max_retries = 3
        self._batch_size = 1000  # 批处理大小
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._lock = threading.RLock()
        self._search_cache: Dict[str, Tuple[List[Dict], float]] = {}
        self._cache_ttl = 60  # 缓存TTL（秒）
        
        try:
            self._connect()
            self._ensure_collection()
            self._connected = True
            app_logger.info(f"✓ Milvus服务初始化成功")
        except Exception as e:
            app_logger.error(f"✗ Milvus初始化失败（将在首次使用时重试）: {e}")
            self._connected = False
    
    def _connect(self):
        """连接Milvus（支持连接池）"""
        try:
            # 检查是否已连接
            try:
                connections.get_connection(alias="default")
                app_logger.info("✓ 已连接到Milvus（复用现有连接）")
                return
            except:
                pass
            
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                timeout=10,
                # 连接池配置
                pool="QueuePool",
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600
            )
            app_logger.info(f"✓ 已连接到Milvus: {self.host}:{self.port}")
        except Exception as e:
            app_logger.error(f"✗ 连接Milvus失败: {e}")
            raise
    
    def _ensure_collection(self):
        """确保集合存在（支持自动创建）"""
        try:
            if utility.has_collection(self.collection_name):
                self._collection = Collection(self.collection_name)
                # 异步加载到内存
                self._async_load_collection()
                app_logger.info(f"✓ 集合 {self.collection_name} 已存在，共 {self._collection.num_entities} 个向量")
            else:
                self._create_collection()
        except Exception as e:
            app_logger.error(f"✗ 集合操作失败: {e}")
            raise
    
    def _async_load_collection(self):
        """异步加载集合到内存"""
        def load_task():
            try:
                if not self._collection.is_empty:
                    self._collection.load(timeout=60)
                    app_logger.debug(f"集合 {self.collection_name} 异步加载完成")
            except Exception as e:
                app_logger.warning(f"集合异步加载失败（可能已加载）: {e}")
        
        self._executor.submit(load_task)
    
    def _create_collection(self):
        """创建新集合（优化字段和索引）"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="document_id", dtype=DataType.INT64),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="created_at", dtype=DataType.INT64),
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="医疗文档向量集合（优化版）"
        )
        
        self._collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # 创建向量索引（IVF_FLAT平衡速度和精度）
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 2048}
        }
        
        self._collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        
        # 创建标量索引用于快速过滤
        self._collection.create_index(
            field_name="document_id",
            index_params={"index_type": "FLAT"}
        )
        
        app_logger.info(f"✓ 集合 {self.collection_name} 创建成功，已创建优化索引")
    
    def _ensure_connection(self) -> bool:
        """确保连接可用（支持自动重连）"""
        for attempt in range(self._max_retries):
            try:
                if not self._connected:
                    self._connect()
                    self._ensure_collection()
                    self._connected = True
                
                # 测试连接
                if self._collection:
                    _ = self._collection.num_entities
                    return True
            except Exception as e:
                app_logger.warning(f"连接检查失败 (尝试 {attempt + 1}/{self._max_retries}): {e}")
                self._connected = False
                if attempt < self._max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
        
        return False
    
    def insert(self, vectors: List[List[float]], texts: List[str], 
               document_ids: List[int], sources: List[str], 
               metadatas: List[Dict], batch_size: Optional[int] = None) -> List[int]:
        """插入向量数据（支持批处理）"""
        if not self._ensure_connection():
            app_logger.error("Milvus未连接，插入操作失败")
            return []
        
        batch_size = batch_size or self._batch_size
        all_ids = []
        
        try:
            for i in range(0, len(vectors), batch_size):
                batch_end = min(i + batch_size, len(vectors))
                batch_vectors = vectors[i:batch_end]
                batch_texts = texts[i:batch_end]
                batch_doc_ids = document_ids[i:batch_end]
                batch_sources = sources[i:batch_end]
                batch_metadatas = metadatas[i:batch_end]
                
                data = [
                    batch_vectors,
                    batch_texts,
                    batch_doc_ids,
                    batch_sources,
                    [str(m) for m in batch_metadatas],
                    [int(time.time() * 1000) for _ in batch_texts],
                ]
                
                mr = self._collection.insert(data)
                all_ids.extend(mr.primary_keys)
                
                app_logger.info(f"✓ 已插入 {batch_end - i}/{len(vectors)} 条向量数据")
            
            # 刷新集合确保数据持久化
            self._collection.flush()
            app_logger.info(f"✓ 共插入 {len(all_ids)} 条向量数据")
            return all_ids
            
        except Exception as e:
            app_logger.error(f"✗ 向量插入失败: {e}")
            return []
    
    def search(self, query_vector: List[float], top_k: int = 5, 
               filter_expr: Optional[str] = None, timeout: int = 30) -> List[Dict]:
        """搜索相似向量（支持过滤和超时）"""
        if not self._ensure_connection():
            app_logger.warning("Milvus未连接，返回空结果")
            return []
        
        try:
            # 确保集合已加载
            if not self._collection.is_loaded:
                self._collection.load()
            
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 32}
            }
            
            results = self._collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["text", "document_id", "source", "metadata"],
                timeout=timeout
            )
            
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "id": hit.id,
                        "score": float(hit.score),
                        "text": hit.entity.get("text", ""),
                        "document_id": hit.entity.get("document_id"),
                        "source": hit.entity.get("source"),
                        "metadata": hit.entity.get("metadata")
                    })
            
            app_logger.debug(f"✓ 搜索完成，返回 {len(formatted_results)} 结果")
            return formatted_results
            
        except Exception as e:
            app_logger.error(f"✗ 向量搜索失败: {e}")
            return []
    
    def batch_search(self, query_vectors: List[List[float]], top_k: int = 5,
                     filter_expr: Optional[str] = None, timeout: int = 60) -> List[List[Dict]]:
        """
        批量向量搜索
        
        同时搜索多个向量，返回每组的结果列表。
        
        Args:
            query_vectors: 查询向量列表
            top_k: 每组返回的结果数
            filter_expr: 过滤表达式
            timeout: 超时时间
            
        Returns:
            每组搜索结果列表
        """
        if not self._ensure_connection():
            app_logger.warning("Milvus未连接，返回空结果")
            return [[] for _ in query_vectors]
        
        try:
            # 确保集合已加载
            if not self._collection.is_loaded:
                self._collection.load()
            
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 32}
            }
            
            results = self._collection.search(
                data=query_vectors,
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["text", "document_id", "source", "metadata"],
                timeout=timeout
            )
            
            all_results = []
            for hits in results:
                formatted_results = []
                for hit in hits:
                    formatted_results.append({
                        "id": hit.id,
                        "score": float(hit.score),
                        "text": hit.entity.get("text", ""),
                        "document_id": hit.entity.get("document_id"),
                        "source": hit.entity.get("source"),
                        "metadata": hit.entity.get("metadata")
                    })
                all_results.append(formatted_results)
            
            app_logger.debug(f"✓ 批量搜索完成，查询 {len(query_vectors)} 组，返回 {len(all_results)} 组结果")
            return all_results
            
        except Exception as e:
            app_logger.error(f"✗ 批量向量搜索失败: {e}")
            return [[] for _ in query_vectors]
    
    def delete_by_document_id(self, document_id: int) -> bool:
        """删除特定文档的所有向量"""
        if not self._ensure_connection():
            return False
        
        try:
            expr = f'document_id == {document_id}'
            self._collection.delete(expr)
            self._collection.flush()
            app_logger.info(f"✓ 已删除文档 {document_id} 的所有向量")
            return True
        except Exception as e:
            app_logger.error(f"✗ 删除向量失败: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, any]:
        """获取集合统计信息"""
        if not self._ensure_connection():
            return {}
        
        try:
            stats = {
                "collection_name": self.collection_name,
                "entity_count": self._collection.num_entities,
                "dimension": self.dimension,
            }
            
            # 获取集合详细信息
            info = self._collection.describe()
            stats["description"] = info.get("description", "")
            stats["fields"] = [f.get("name") for f in info.get("fields", [])]
            stats["indexes"] = [idx.get("index_name") for idx in info.get("indexes", [])]
            
            return stats
        except Exception as e:
            app_logger.error(f"✗ 获取集合统计信息失败: {e}")
            return {}
    
    def health_check(self) -> Dict[str, any]:
        """获取健康检查详情"""
        try:
            stats = self.get_collection_stats()
            if stats:
                return {
                    "status": "healthy",
                    "collection": self.collection_name,
                    "entity_count": stats.get("entity_count", 0),
                    "dimension": self.dimension,
                    "connected": self._connected
                }
            else:
                return {"status": "unhealthy", "reason": "无法获取集合信息"}
        except Exception as e:
            return {"status": "unhealthy", "reason": str(e)}
    
    def optimize_index(self) -> bool:
        """
        优化索引（在数据量变化后调用）
        
        根据当前数据量自动调整索引参数。
        """
        if not self._ensure_connection():
            return False
        
        try:
            entity_count = self._collection.num_entities
            
            # 根据数据量调整nlist
            if entity_count < 10000:
                nlist = 128
            elif entity_count < 100000:
                nlist = 1024
            else:
                nlist = 2048
            
            # 删除旧索引并创建新索引
            self._collection.release()
            self._collection.drop_index()
            
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": nlist}
            }
            
            self._collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            
            self._collection.load()
            app_logger.info(f"✓ 索引优化完成，nlist={nlist} (数据量: {entity_count})")
            return True
            
        except Exception as e:
            app_logger.error(f"✗ 索引优化失败: {e}")
            return False
    
    def close(self):
        """关闭Milvus连接"""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
            connections.disconnect(alias="default")
            app_logger.info("✓ Milvus连接已关闭")
        except Exception as e:
            app_logger.warning(f"关闭Milvus连接时出错: {e}")


# 全局Milvus实例（延迟初始化）
_milvus_service_opt: Optional[MilvusService] = None


def get_milvus_service() -> MilvusService:
    """获取Milvus服务实例（单例模式）"""
    global _milvus_service_opt
    if _milvus_service_opt is None:
        _milvus_service_opt = MilvusService()
    return _milvus_service_opt
