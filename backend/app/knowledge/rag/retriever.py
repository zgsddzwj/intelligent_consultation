"""RAG检索器"""
from typing import List, Dict, Any
from app.knowledge.rag.embedder import Embedder
from app.services.milvus_service import get_milvus_service
from app.utils.logger import app_logger


class Retriever:
    """RAG检索器"""
    
    def __init__(self):
        self.embedder = Embedder()
        self._milvus = None
    
    @property
    def milvus(self):
        """延迟获取Milvus服务"""
        if self._milvus is None:
            self._milvus = get_milvus_service()
        return self._milvus
    
    def retrieve(self, query: str, top_k: int = 5, 
                 filter_expr: str = None) -> List[Dict[str, Any]]:
        """检索相关文档"""
        try:
            # 将查询转换为向量
            query_vector = self.embedder.embed_query(query)
            
            # 在Milvus中搜索
            results = self.milvus.search(
                query_vector=query_vector,
                top_k=top_k,
                filter_expr=filter_expr
            )
            
            # 格式化结果，添加来源信息
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result.get("text"),
                    "source": result.get("source"),
                    "metadata": result.get("metadata"),
                    "score": result.get("score"),
                    "document_id": result.get("document_id")
                })
            
            app_logger.info(f"检索到 {len(formatted_results)} 条相关文档")
            return formatted_results
            
        except Exception as e:
            app_logger.warning(f"RAG检索失败（将返回空结果）: {e}")
            # 返回空结果而不是抛出异常，允许系统继续工作
            return []
    
    def format_context(self, results: List[Dict[str, Any]]) -> str:
        """格式化检索结果为上下文"""
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("source", "未知来源")
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            
            # 构建来源标注
            citation = f"[来源: {source}"
            if metadata.get("page"):
                citation += f", 页码: {metadata['page']}"
            if metadata.get("section"):
                citation += f", 章节: {metadata['section']}"
            citation += "]"
            
            context_parts.append(f"{citation}\n{text}")
        
        return "\n\n".join(context_parts)

