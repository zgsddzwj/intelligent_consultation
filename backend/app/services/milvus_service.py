"""Milvus向量数据库服务"""
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
from typing import List, Dict, Optional
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class MilvusService:
    """Milvus服务类"""
    
    def __init__(self):
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = 1024  # Qwen embedding维度
        self._collection: Optional[Collection] = None
        self._connected = False
        try:
            self._connect()
            self._ensure_collection()
            self._connected = True
        except Exception as e:
            app_logger.warning(f"Milvus初始化失败，将在首次使用时重试: {e}")
            self._connected = False
    
    def _connect(self):
        """连接Milvus"""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            app_logger.info(f"已连接到Milvus: {self.host}:{self.port}")
        except Exception as e:
            app_logger.error(f"连接Milvus失败: {e}")
            raise
    
    def _ensure_collection(self):
        """确保集合存在"""
        if utility.has_collection(self.collection_name):
            self._collection = Collection(self.collection_name)
            app_logger.info(f"集合 {self.collection_name} 已存在")
        else:
            self._create_collection()
    
    def _create_collection(self):
        """创建集合"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="document_id", dtype=DataType.INT64),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="医疗文档向量集合"
        )
        
        self._collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # 创建索引
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        self._collection.create_index(
            field_name="vector",
            index_params=index_params
        )
        
        app_logger.info(f"集合 {self.collection_name} 创建成功")
    
    def insert(self, vectors: List[List[float]], texts: List[str], 
               document_ids: List[int], sources: List[str], 
               metadatas: List[Dict]) -> List[int]:
        """插入向量数据"""
        if not self._connected:
            try:
                self._connect()
                self._ensure_collection()
                self._connected = True
            except Exception as e:
                raise ValueError(f"Milvus未连接: {e}")
        
        if not self._collection:
            raise ValueError("集合未初始化")
        
        # 准备数据
        data = [
            vectors,
            texts,
            document_ids,
            sources,
            [str(m) for m in metadatas]  # 将metadata转为字符串
        ]
        
        # 插入数据
        mr = self._collection.insert(data)
        self._collection.flush()
        
        app_logger.info(f"插入了 {len(vectors)} 条向量数据")
        return mr.primary_keys
    
    def search(self, query_vector: List[float], top_k: int = 5, 
               filter_expr: Optional[str] = None) -> List[Dict]:
        """搜索相似向量"""
        if not self._connected:
            try:
                self._connect()
                self._ensure_collection()
                self._connected = True
            except Exception as e:
                app_logger.error(f"Milvus连接失败: {e}")
                return []  # 返回空列表而不是抛出异常
        
        if not self._collection:
            return []
        
        # 加载集合
        self._collection.load()
        
        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        # 执行搜索
        results = self._collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["text", "document_id", "source", "metadata"]
        )
        
        # 格式化结果
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.entity.get("text"),
                    "document_id": hit.entity.get("document_id"),
                    "source": hit.entity.get("source"),
                    "metadata": hit.entity.get("metadata")
                })
        
        return formatted_results
    
    def delete_by_document_id(self, document_id: int):
        """根据文档ID删除向量"""
        if not self._collection:
            raise ValueError("集合未初始化")
        
        expr = f'document_id == {document_id}'
        self._collection.delete(expr)
        self._collection.flush()
        app_logger.info(f"删除了文档 {document_id} 的所有向量")


# 全局Milvus实例（延迟初始化）
_milvus_service: Optional[MilvusService] = None

def get_milvus_service() -> MilvusService:
    """获取Milvus服务实例（单例模式）"""
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service

# 为了向后兼容，创建一个类来模拟实例
class MilvusServiceProxy:
    """Milvus服务代理"""
    def __getattr__(self, name):
        return getattr(get_milvus_service(), name)

milvus_service = MilvusServiceProxy()

