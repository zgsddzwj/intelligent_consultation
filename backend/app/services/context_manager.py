"""上下文管理服务 - 对话历史、分层上下文和智能压缩"""
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.utils.logger import app_logger
from app.services.llm_service import llm_service

settings = get_settings()


class ContextManager:
    """上下文管理器"""
    
    def __init__(self):
        self.max_tokens = settings.CONTEXT_MAX_TOKENS
        self.history_limit = settings.CONTEXT_HISTORY_LIMIT
        self.compression_enabled = settings.CONTEXT_COMPRESSION_ENABLED
    
    def build_context(self, messages: List[Dict[str, str]], 
                     current_query: str,
                     short_term_limit: int = None,
                     include_summary: bool = True) -> Dict[str, Any]:
        """
        构建分层上下文
        
        Args:
            messages: 历史消息列表
            current_query: 当前查询
            short_term_limit: 短期上下文轮次限制
            include_summary: 是否包含摘要
        
        Returns:
            上下文字典，包含：
                - short_term: 短期上下文（最近N轮）
                - medium_term: 中期上下文（本次会话摘要）
                - long_term: 长期上下文（用户历史摘要）
                - full_context: 完整上下文文本
        """
        short_term_limit = short_term_limit or self.history_limit
        
        # 1. 短期上下文：最近N轮对话
        short_term = self._extract_short_term(messages, short_term_limit)
        
        # 2. 中期上下文：本次会话摘要
        medium_term = None
        if include_summary and len(messages) > short_term_limit:
            medium_term = self._create_session_summary(messages[:-short_term_limit])
        
        # 3. 长期上下文：用户历史摘要（从metadata中获取）
        long_term = None  # 可以从用户档案中获取
        
        # 4. 构建完整上下文
        full_context = self._combine_context(short_term, medium_term, long_term, current_query)
        
        # 5. 检查是否需要压缩
        if self.compression_enabled:
            estimated_tokens = self._estimate_tokens(full_context)
            if estimated_tokens > self.max_tokens:
                app_logger.info(f"上下文超过token限制 ({estimated_tokens} > {self.max_tokens})，进行压缩")
                full_context = self._compress_context(full_context, current_query)
        
        return {
            "short_term": short_term,
            "medium_term": medium_term,
            "long_term": long_term,
            "full_context": full_context,
            "estimated_tokens": self._estimate_tokens(full_context)
        }
    
    def _extract_short_term(self, messages: List[Dict], limit: int) -> List[Dict]:
        """提取短期上下文（最近N轮）"""
        return messages[-limit * 2:] if len(messages) > limit * 2 else messages
    
    def _create_session_summary(self, messages: List[Dict]) -> str:
        """创建会话摘要"""
        if not messages:
            return ""
        
        # 提取关键信息
        key_info = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                # 提取用户问题中的关键信息
                key_info.append(f"用户询问: {content[:200]}")
            elif role == "assistant":
                # 提取回答中的关键信息
                key_info.append(f"回答要点: {content[:200]}")
        
        summary_text = "\n".join(key_info)
        
        # 如果摘要太长，使用LLM进一步压缩
        if len(summary_text) > 1000:
            try:
                summary_prompt = f"""请将以下对话历史压缩为关键信息摘要，保留重要的医疗信息（症状、诊断、用药等）：

{summary_text}

请提供简洁的摘要："""
                summary = llm_service.generate(
                    prompt=summary_prompt,
                    temperature=0.3,
                    max_tokens=500
                )
                return summary
            except Exception as e:
                app_logger.warning(f"创建会话摘要失败: {e}")
                return summary_text[:1000]
        
        return summary_text
    
    def _combine_context(self, short_term: List[Dict], medium_term: Optional[str],
                        long_term: Optional[str], current_query: str) -> str:
        """组合上下文"""
        context_parts = []
        
        # 长期上下文
        if long_term:
            context_parts.append(f"用户历史信息：\n{long_term}\n")
        
        # 中期上下文（会话摘要）
        if medium_term:
            context_parts.append(f"本次会话摘要：\n{medium_term}\n")
        
        # 短期上下文（最近对话）
        if short_term:
            context_parts.append("最近对话：\n")
            for msg in short_term:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    context_parts.append(f"用户: {content}\n")
                elif role == "assistant":
                    context_parts.append(f"助手: {content}\n")
        
        # 当前查询
        context_parts.append(f"\n当前问题：{current_query}")
        
        return "\n".join(context_parts)
    
    def _compress_context(self, context: str, current_query: str) -> str:
        """压缩上下文"""
        from app.services.context_compressor import context_compressor
        return context_compressor.compress(context, current_query)
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算token数量（优化版）
        
        策略：
        1. 尝试使用 tiktoken (如果可用)
        2. 回退到启发式算法：
           - ASCII字符（英文/数字）：约 4 char = 1 token
           - 非ASCII字符（中文等）：约 1 char = 1 token (保守估计)
        """
        try:
            import tiktoken
            # 使用 cl100k_base (GPT-4/3.5, Qwen等常用编码)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            # 启发式计算
            token_count = 0
            for char in text:
                if ord(char) < 128:
                    token_count += 0.25
                else:
                    token_count += 1.0  # 中文通常 0.7~1.5 token/char，取 1 保守
            return int(token_count)
    
    def retrieve_relevant_history(self, current_query: str, 
                                  all_messages: List[Dict],
                                  top_k: int = 5) -> List[Dict]:
        """检索相关历史对话"""
        # 简化版：基于关键词匹配
        # 实际可以使用embedding相似度检索
        
        query_keywords = set(current_query.lower().split())
        scored_messages = []
        
        for msg in all_messages:
            content = msg.get("content", "").lower()
            msg_keywords = set(content.split())
            
            # 计算关键词重叠度
            overlap = len(query_keywords & msg_keywords)
            if overlap > 0:
                scored_messages.append((overlap, msg))
        
        # 按分数排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        return [msg for _, msg in scored_messages[:top_k]]


# 全局实例
context_manager = ContextManager()

