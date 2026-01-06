"""RAG检索工具"""
from typing import Dict, Any, List
from app.knowledge.rag.hybrid_search import HybridSearch
from app.utils.logger import app_logger


class RAGTool:
    """RAG检索工具"""
    
    def __init__(self):
        self.name = "rag_search"
        self.description = "检索医疗文献和文档，获取相关医疗信息"
        self.hybrid_search = HybridSearch()
    
    def execute(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """执行RAG检索"""
        try:
            results = self.hybrid_search.hybrid_search(query, top_k=top_k)
            
            # 格式化结果
            formatted_results = {
                "query": query,
                "results": results,
                "count": len(results)
            }
            
            app_logger.info(f"RAG检索完成: {query}, 返回 {len(results)} 条结果")
            return formatted_results
        except Exception as e:
            app_logger.error(f"RAG检索失败: {e}")
            return {
                "query": query,
                "results": [],
                "count": 0,
                "error": str(e)
            }
    
    def format_context(self, results: Dict[str, Any]) -> str:
        """格式化检索结果为上下文"""
        if not results.get("results"):
            return "未找到相关医疗文献。"
        
        context_parts = []
        for i, result in enumerate(results["results"], 1):
            source = result.get("source", "未知来源")
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            
            citation = f"[来源{i}: {source}"
            if isinstance(metadata, dict):
                if metadata.get("page"):
                    citation += f", 页码: {metadata['page']}"
                if metadata.get("section"):
                    citation += f", 章节: {metadata['section']}"
            citation += "]"
            
            context_parts.append(f"{citation}\n{text}")
        
        return "\n\n".join(context_parts)

