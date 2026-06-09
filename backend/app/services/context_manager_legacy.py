"""上下文管理服务 - v1.0 遗留版本（向后兼容）"""
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
    """线程安全的LRU缓存"""
    
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
    """上下文管理器 v1.0 - 基础版本（向后兼容）"""
    
    def __init__(self):
        self.max_tokens = getattr(settings, 'CONTEXT_MAX_TOKENS', 4000)
        self.history_limit = getattr(settings, 'CONTEXT_HISTORY_LIMIT', 10)
        self.compression_enabled = getattr(settings, 'CONTEXT_COMPRESSION_ENABLED', True)
        self._summary_cache = LRUCache(max_size=200)
        
        self._token_budget = {
            "short_term": 0.5,
            "medium_term": 0.3,
            "long_term": 0.15,
            "current_query": 0.05
        }
    
    def build_context(self, messages: List[Dict[str, str]], 
                     current_query: str,
                     short_term_limit: int = None) -> Dict[str, Any]:
        """构建分层上下文"""
        short_term_limit = short_term_limit or self.history_limit
        budgets = self._calculate_budgets(self.max_tokens)
        
        short_term = self._extract_short_term(messages, short_term_limit)
        short_term_text = self._format_messages(short_term)
        short_term_tokens = self._estimate_tokens(short_term_text)
        
        if short_term_tokens > budgets["short_term"]:
            short_term = self._truncate_messages_by_tokens(short_term, budgets["short_term"])
            short_term_text = self._format_messages(short_term)
        
        medium_term_text = ""
        if len(messages) > len(short_term):
            medium_term_text = self._get_cached_summary(messages[:-len(short_term)], budgets["medium_term"])
        
        long_term_text = ""
        full_context = self._combine_context(short_term_text, medium_term_text, long_term_text, current_query)
        
        estimated_tokens = self._estimate_tokens(full_context)
        if self.compression_enabled and estimated_tokens > self.max_tokens:
            full_context = self._smart_compress(full_context, current_query, self.max_tokens)
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
        return {
            "short_term": int(total_tokens * self._token_budget["short_term"]),
            "medium_term": int(total_tokens * self._token_budget["medium_term"]),
            "long_term": int(total_tokens * self._token_budget["long_term"]),
            "current_query": int(total_tokens * self._token_budget["current_query"])
        }
    
    def _extract_short_term(self, messages: List[Dict], limit: int) -> List[Dict]:
        return messages[-limit * 2:] if len(messages) > limit * 2 else messages
    
    def _format_messages(self, messages: List[Dict]) -> str:
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
        cache_key = self._generate_summary_key(messages)
        cached = self._summary_cache.get(cache_key)
        if cached:
            return cached
        summary = self._create_session_summary(messages, max_tokens)
        self._summary_cache.put(cache_key, summary)
        return summary
    
    def _generate_summary_key(self, messages: List[Dict]) -> str:
        content = "|".join([f"{m.get('role', '')}:{m.get('content', '')[:100]}" for m in messages])
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _create_session_summary(self, messages: List[Dict], max_tokens: int = 500) -> str:
        if not messages:
            return ""
        key_info = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                key_info.append(f"用户询问: {content[:200]}")
            elif role == "assistant":
                key_info.append(f"回答要点: {content[:200]}")
        summary_text = "\n".join(key_info)
        if self._estimate_tokens(summary_text) > max_tokens:
            return summary_text[:1000]
        return summary_text
    
    def _combine_context(self, short_term: str, medium_term: Optional[str],
                        long_term: Optional[str], current_query: str) -> str:
        context_parts = []
        if long_term:
            context_parts.append(f"用户历史信息：\n{long_term}\n")
        if medium_term:
            context_parts.append(f"本次会话摘要：\n{medium_term}\n")
        if short_term:
            context_parts.append(f"最近对话：\n{short_term}\n")
        context_parts.append(f"当前问题：{current_query}")
        return "\n".join(context_parts)
    
    def _smart_compress(self, context: str, current_query: str, target_tokens: int) -> str:
        current_tokens = self._estimate_tokens(context)
        if current_tokens <= target_tokens:
            return context
        try:
            from app.services.context_compressor import context_compressor
            compressed = context_compressor.compress(context, current_query)
            if self._estimate_tokens(compressed) <= target_tokens:
                return compressed
        except Exception:
            pass
        lines = context.split("\n")
        result_lines = []
        current_count = 0
        for line in lines:
            line_tokens = self._estimate_tokens(line)
            if current_count + line_tokens > target_tokens * 0.9:
                break
            result_lines.append(line)
            current_count += line_tokens
        return "\n".join(result_lines)
    
    def _estimate_tokens(self, text: str) -> int:
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
    
    def clear_cache(self):
        self._summary_cache.clear()


# v1.0 实例
context_manager_v1 = ContextManager()
