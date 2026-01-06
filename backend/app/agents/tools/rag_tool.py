"""RAG检索工具 - 增强版，支持高级RAG"""
from typing import Dict, Any, List, Optional
from app.knowledge.rag.hybrid_search import HybridSearch
from app.knowledge.rag.advanced_rag import AdvancedRAG
from app.utils.logger import app_logger


class RAGTool:
    """RAG检索工具 - 支持高级RAG和传统检索"""
    
    def __init__(self, use_advanced: bool = True):
        """
        初始化RAG工具
        
        Args:
            use_advanced: 是否使用高级RAG（默认True）
        """
        self.name = "rag_search"
        self.description = "检索医疗文献和文档，获取相关医疗信息"
        self.use_advanced = use_advanced
        self.hybrid_search = HybridSearch(use_advanced=use_advanced)
        self.advanced_rag = AdvancedRAG() if use_advanced else None
    
    def execute(self, query: str, top_k: int = 5, use_advanced: Optional[bool] = None) -> Dict[str, Any]:
        """
        执行RAG检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_advanced: 是否使用高级RAG（None表示使用初始化时的设置）
        """
        use_advanced = use_advanced if use_advanced is not None else self.use_advanced
        
        # 如果启用高级RAG，使用高级RAG系统
        if use_advanced and self.advanced_rag:
            try:
                result = self.advanced_rag.retrieve(query, top_k=top_k)
                
                # 转换为兼容格式
                formatted_results = {
                    "query": query,
                    "results": result.get("documents", []),
                    "count": len(result.get("documents", [])),
                    "intent": result.get("intent"),
                    "query_analysis": result.get("query_analysis"),
                    "stats": result.get("stats", {})
                }
                
                app_logger.info(f"高级RAG检索完成: {query}, 返回 {formatted_results['count']} 条结果")
                return formatted_results
            except Exception as e:
                app_logger.warning(f"高级RAG检索失败，降级到传统检索: {e}")
        
        # 传统检索（向后兼容）
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
        
        # 如果使用高级RAG，使用高级RAG的格式化方法
        if self.use_advanced and self.advanced_rag and results.get("intent"):
            try:
                return self.advanced_rag.format_context(results)
            except Exception as e:
                app_logger.warning(f"高级RAG格式化失败，使用传统格式化: {e}")
        
        # 传统格式化（向后兼容）
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
            # 添加相关性分数（如果有）
            if "final_score" in result:
                citation += f", 相关性: {result['final_score']:.2f}"
            citation += "]"
            
            context_parts.append(f"{citation}\n{text}")
        
        return "\n\n".join(context_parts)

