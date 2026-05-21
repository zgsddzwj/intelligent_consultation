"""上下文管理服务 - 增强版（智能摘要缓存、对话轮次优化、Token预算分配）"""
import math
import hashlib
import threading
import time
from typing import List, Dict, Any, Optional
from collections import OrderedDict
from app.config import get_settings
from app.utils.logger import app_logger
from app.services.llm_service import llm_service

settings = get_settings()


class LRUCache:
    """线程安全的LRU缓存（用于摘要缓存）"""
    
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def put(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
    def clear(self):
        with self._lock:
            self._cache.clear()


class ContextManager:
    """上下文管理器（增强版）
    
    新增功能：
    - 智能摘要缓存（LRU）
    - Token预算分配
    - 对话轮次动态优化
    - 上下文压缩策略选择
    """
    
    def __init__(self):
        self.max_tokens = settings.CONTEXT_MAX_TOKENS
        self.history_limit = settings.CONTEXT_HISTORY_LIMIT
        self.compression_enabled = settings.CONTEXT_COMPRESSION_ENABLED
        
        # 摘要缓存
        self._summary_cache = LRUCache(max_size=200)
        
        # Token预算分配比例
        self._token_budget = {
            "short_term": 0.5,
            "medium_term": 0.3,
            "long_term": 0.15,
            "current_query": 0.05
        }
    
    def build_context(self, messages: List[Dict[str, str]], 
                     current_query: str,
                     short_term_limit: int = None,
                     include_summary: bool = True) -> Dict[str, Any]:
        """构建分层上下文（带Token预算分配）"""
        short_term_limit = short_term_limit or self.history_limit
        
        budgets = self._calculate_budgets(self.max_tokens)
        
        # 1. 短期上下文
        short_term = self._extract_short_term(messages, short_term_limit)
        short_term_text = self._format_messages(short_term)
        short_term_tokens = self._estimate_tokens(short_term_text)
        
        if short_term_tokens > budgets["short_term"]:
            short_term = self._truncate_messages_by_tokens(
                short_term, budgets["short_term"]
            )
            short_term_text = self._format_messages(short_term)
        
        # 2. 中期上下文（带缓存）
        medium_term_text = ""
        if include_summary and len(messages) > len(short_term):
            medium_term_text = self._get_cached_summary(
                messages[:-len(short_term)], budgets["medium_term"]
            )
        
        # 3. 长期上下文
        long_term_text = ""
        
        # 4. 构建完整上下文
        full_context = self._combine_context(
            short_term_text, medium_term_text, long_term_text, current_query
        )
        
        # 5. 智能压缩
        estimated_tokens = self._estimate_tokens(full_context)
        if self.compression_enabled and estimated_tokens > self.max_tokens:
            app_logger.info(
                f"上下文超过token限制 ({estimated_tokens} > {self.max_tokens})，进行智能压缩"
            )
            full_context = self._smart_compress(
                full_context, current_query, self.max_tokens
            )
            estimated_tokens = self._estimate_tokens(full_context)
        
        return {
            "short_term": short_term,
            "medium_term": medium_term_text,
            "long_term": long_term_text,
            "full_context": full_context,
            "estimated_tokens": estimated_tokens,
            "token_budgets": budgets
        }
    
    def _calculate_budgets(self, total_tokens: int) -> Dict[str, int]:
        """计算各部分的Token预算"""
        return {
            "short_term": int(total_tokens * self._token_budget["short_term"]),
            "medium_term": int(total_tokens * self._token_budget["medium_term"]),
            "long_term": int(total_tokens * self._token_budget["long_term"]),
            "current_query": int(total_tokens * self._token_budget["current_query"])
        }
    
    def _extract_short_term(self, messages: List[Dict], limit: int) -> List[Dict]:
        """提取短期上下文（最近N轮）"""
        return messages[-limit * 2:] if len(messages) > limit * 2 else messages
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """格式化消息列表为文本"""
        parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                parts.append(f"用户: {content}")
            elif role == "assistant":
                parts.append(f"助手: {content}")
        return "\n".join(parts)
    
    def _truncate_messages_by_tokens(self, messages: List[Dict], max_tokens: int) -> List[Dict]:
        """按Token预算截断消息列表（保留最近的消息）"""
        result = []
        current_tokens = 0
        
        for msg in reversed(messages):
            msg_text = f"{msg.get('role', '')}: {msg.get('content', '')}"
            msg_tokens = self._estimate_tokens(msg_text)
            
            if current_tokens + msg_tokens > max_tokens and result:
                break
            
            result.insert(0, msg)
            current_tokens += msg_tokens
        
        return result
    
    def _get_cached_summary(self, messages: List[Dict], max_tokens: int) -> str:
        """获取缓存的摘要（带LRU缓存）"""
        # 生成缓存键
        cache_key = self._generate_summary_key(messages)
        
        # 尝试从缓存获取
        cached = self._summary_cache.get(cache_key)
        if cached:
            app_logger.debug("摘要缓存命中")
            return cached
        
        # 生成新摘要
        summary = self._create_session_summary(messages, max_tokens)
        
        # 存入缓存
        self._summary_cache.put(cache_key, summary)
        
        return summary
    
    def _generate_summary_key(self, messages: List[Dict]) -> str:
        """生成消息列表的摘要缓存键"""
        # 使用消息内容的哈希作为缓存键
        content = "|".join([
            f"{m.get('role', '')}:{m.get('content', '')[:100]}"
            for m in messages
        ])
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _create_session_summary(self, messages: List[Dict], max_tokens: int = 500) -> str:
        """创建会话摘要（优化版，带token限制）"""
        if not messages:
            return ""
        
        # 提取关键信息
        key_info = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                key_info.append(f"用户询问: {content[:200]}")
            elif role == "assistant":
                key_info.append(f"回答要点: {content[:200]}")
        
        summary_text = "\n".join(key_info)
        
        # 如果摘要太长，使用LLM进一步压缩
        if self._estimate_tokens(summary_text) > max_tokens:
            try:
                summary_prompt = f"""请将以下对话历史压缩为关键信息摘要，保留重要的医疗信息（症状、诊断、用药等），控制在{max_tokens}个token内：

{summary_text[:2000]}

请提供简洁的摘要："""
                summary = llm_service.generate(
                    prompt=summary_prompt,
                    temperature=0.3,
                    max_tokens=max_tokens
                )
                return summary
            except Exception as e:
                app_logger.warning(f"创建会话摘要失败: {e}")
                return summary_text[:1000]
        
        return summary_text
    
    def _combine_context(self, short_term: str, medium_term: Optional[str],
                        long_term: Optional[str], current_query: str) -> str:
        """组合上下文（按重要性排序）"""
        context_parts = []
        
        # 长期上下文
        if long_term:
            context_parts.append(f"用户历史信息：\n{long_term}\n")
        
        # 中期上下文（会话摘要）
        if medium_term:
            context_parts.append(f"本次会话摘要：\n{medium_term}\n")
        
        # 短期上下文（最近对话）
        if short_term:
            context_parts.append(f"最近对话：\n{short_term}\n")
        
        # 当前查询
        context_parts.append(f"当前问题：{current_query}")
        
        return "\n".join(context_parts)
    
    def _smart_compress(self, context: str, current_query: str, target_tokens: int) -> str:
        """智能压缩上下文（多策略）"""
        current_tokens = self._estimate_tokens(context)
        
        if current_tokens <= target_tokens:
            return context
        
        # 策略1: 尝试使用上下文压缩器
        try:
            from app.services.context_compressor import context_compressor
            compressed = context_compressor.compress(context, current_query)
            if self._estimate_tokens(compressed) <= target_tokens:
                return compressed
        except Exception:
            pass
        
        # 策略2: 按比例截断各部分
        lines = context.split("\n")
        result_lines = []
        current_count = 0
        
        # 保留当前查询和关键信息
        for line in lines:
            line_tokens = self._estimate_tokens(line)
            if current_count + line_tokens > target_tokens * 0.9:
                break
            result_lines.append(line)
            current_count += line_tokens
        
        return "\n".join(result_lines)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量（优化版）"""
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            ascii_chars = 0
            other_chars = 0
            for char in text:
                if ord(char) < 128:
                    ascii_chars += 1
                else:
                    other_chars += 1
            
            ascii_tokens = math.ceil(ascii_chars / 4.0)
            other_tokens = math.ceil(other_chars / 1.5)
            
            return ascii_tokens + other_tokens
    
    def retrieve_relevant_history(self, current_query: str, 
                                  all_messages: List[Dict],
                                  top_k: int = 5) -> List[Dict]:
        """检索相关历史对话（增强版，支持TF-IDF风格评分）"""
        query_keywords = set(current_query.lower().split())
        scored_messages = []
        
        for msg in all_messages:
            content = msg.get("content", "").lower()
            msg_keywords = set(content.split())
            
            # 计算关键词重叠度
            overlap = len(query_keywords & msg_keywords)
            
            # 计算Jaccard相似度
            union = len(query_keywords | msg_keywords)
            jaccard = overlap / union if union > 0 else 0
            
            # 综合评分
            score = overlap + jaccard * 2
            
            if score > 0:
                scored_messages.append((score, msg))
        
        # 按分数排序
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        return [msg for _, msg in scored_messages[:top_k]]
    
    def clear_cache(self):
        """清空摘要缓存"""
        self._summary_cache.clear()
        app_logger.info("上下文摘要缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_type": "LRU",
            "max_size": self._summary_cache._max_size,
            "current_size": len(self._summary_cache._cache)
        }


# 全局实例
context_manager = ContextManager()
