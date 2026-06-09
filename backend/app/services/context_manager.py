"""上下文管理服务 - v2.0（对话上下文管理优化：历史压缩、Token控制、意图保持）

优化点：
1. 意图感知的历史压缩（保留与当前意图相关的对话）
2. 动态Token预算分配（根据对话复杂度调整）
3. 多层级摘要策略（短期/中期/长期/意图摘要）
4. 意图保持机制（防止话题漂移）
5. 对话状态追踪（话题转移检测）
"""
import math
import hashlib
import threading
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
from app.config import get_settings
from app.utils.logger import app_logger
from app.services.llm_service import llm_service

settings = get_settings()


@dataclass
class DialogueTurn:
    """对话轮次数据类"""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    intent: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    importance_score: float = 0.0


@dataclass
class ConversationState:
    """对话状态"""
    current_topic: str = ""
    previous_topic: str = ""
    topic_switch_count: int = 0
    user_intent: str = ""
    key_entities: List[str] = field(default_factory=list)
    accumulated_questions: List[str] = field(default_factory=list)


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


class IntentAnalyzer:
    """意图分析器 - 识别和追踪用户意图"""
    
    # 医疗意图关键词映射
    INTENT_PATTERNS = {
        "symptom_inquiry": ["症状", "不舒服", "疼", "痛", "难受", "感觉", "表现"],
        "diagnosis_request": ["诊断", "什么病", "得了什么", "怎么回事", "原因"],
        "treatment_inquiry": ["治疗", "怎么办", "怎么治", "疗法", "治愈"],
        "drug_inquiry": ["药", "药物", "吃什么药", "用药", "副作用", "剂量"],
        "prevention_inquiry": ["预防", "防止", "避免", "怎么预防", "注意事项"],
        "lifestyle_inquiry": ["饮食", "运动", "作息", "生活习惯", "保健"],
        "follow_up": ["复查", "复诊", "后续", "接下来", "然后"],
        "emergency": ["急救", "紧急", "严重", "危险", "快", "马上"]
    }
    
    def analyze(self, text: str) -> Tuple[str, float]:
        """分析文本意图，返回(意图类型, 置信度)"""
        text_lower = text.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[intent] = score / len(keywords)
        
        if not scores:
            return "general_inquiry", 0.5
        
        best_intent = max(scores, key=scores.get)
        return best_intent, scores[best_intent]
    
    def extract_entities(self, text: str) -> List[str]:
        """提取医疗实体（简化版）"""
        # 常见医疗实体模式
        entities = []
        
        # 疾病名称模式（简化）
        disease_indicators = ["病", "症", "炎", "癌", "瘤", "梗", "栓", "压"]
        words = text.split()
        for word in words:
            if any(ind in word for ind in disease_indicators) and len(word) >= 2:
                entities.append(word)
        
        # 药物名称模式（简化）
        drug_indicators = ["药", "片", "胶囊", "注射液", "口服液"]
        for word in words:
            if any(ind in word for ind in drug_indicators) and len(word) >= 2:
                entities.append(word)
        
        return list(set(entities))[:10]  # 去重并限制数量


class ContextManagerV2:
    """上下文管理器 v2.0 - 意图感知优化版
    
    核心优化：
    - 意图感知压缩：保留与当前意图相关的历史对话
    - 动态Token预算：根据对话复杂度智能分配
    - 话题转移检测：识别话题切换，保持上下文连贯
    - 多层级摘要：短期记忆 + 中期摘要 + 长期画像 + 意图追踪
    """
    
    def __init__(self):
        self.max_tokens = getattr(settings, 'CONTEXT_MAX_TOKENS', 4000)
        self.history_limit = getattr(settings, 'CONTEXT_HISTORY_LIMIT', 10)
        self.compression_enabled = getattr(settings, 'CONTEXT_COMPRESSION_ENABLED', True)
        
        # 摘要缓存
        self._summary_cache = LRUCache(max_size=200)
        
        # 意图分析器
        self._intent_analyzer = IntentAnalyzer()
        
        # 对话状态
        self._conversation_states: Dict[str, ConversationState] = {}
        
        # 动态Token预算（根据对话阶段调整）
        self._token_budget_phases = {
            "opening": {"short_term": 0.6, "medium_term": 0.2, "long_term": 0.15, "current_query": 0.05},
            "deepening": {"short_term": 0.5, "medium_term": 0.3, "long_term": 0.15, "current_query": 0.05},
            "transitioning": {"short_term": 0.4, "medium_term": 0.35, "long_term": 0.2, "current_query": 0.05},
            "closing": {"short_term": 0.5, "medium_term": 0.3, "long_term": 0.15, "current_query": 0.05}
        }
    
    def build_context(self, messages: List[Dict[str, str]], 
                     current_query: str,
                     session_id: str = "default",
                     short_term_limit: int = None) -> Dict[str, Any]:
        """构建意图感知的分层上下文"""
        short_term_limit = short_term_limit or self.history_limit
        
        # 1. 分析当前意图
        current_intent, intent_confidence = self._intent_analyzer.analyze(current_query)
        current_entities = self._intent_analyzer.extract_entities(current_query)
        
        # 2. 更新对话状态
        state = self._get_or_create_state(session_id)
        self._update_conversation_state(state, current_query, current_intent, current_entities)
        
        # 3. 确定对话阶段
        phase = self._detect_conversation_phase(state, len(messages))
        budgets = self._calculate_budgets(self.max_tokens, phase)
        
        # 4. 构建意图感知的短期上下文
        short_term = self._extract_intent_aware_short_term(
            messages, short_term_limit, current_intent, current_entities
        )
        short_term_text = self._format_messages(short_term)
        short_term_tokens = self._estimate_tokens(short_term_text)
        
        if short_term_tokens > budgets["short_term"]:
            short_term = self._truncate_messages_by_tokens(
                short_term, budgets["short_term"]
            )
            short_term_text = self._format_messages(short_term)
        
        # 5. 构建中期上下文（意图相关的历史摘要）
        medium_term_text = ""
        if len(messages) > len(short_term):
            medium_term_text = self._get_intent_aware_summary(
                messages[:-len(short_term)], current_intent, current_entities, budgets["medium_term"]
            )
        
        # 6. 构建长期上下文（用户画像/关键历史）
        long_term_text = self._build_long_term_context(state, budgets["long_term"])
        
        # 7. 意图保持提示
        intent_preservation = self._build_intent_preservation_prompt(state, current_intent)
        
        # 8. 组合完整上下文
        full_context = self._combine_context_v2(
            short_term_text, medium_term_text, long_term_text, 
            current_query, intent_preservation
        )
        
        # 9. 智能压缩（如果超出限制）
        estimated_tokens = self._estimate_tokens(full_context)
        if self.compression_enabled and estimated_tokens > self.max_tokens:
            app_logger.info(
                f"上下文超过token限制 ({estimated_tokens} > {self.max_tokens})，进行意图感知压缩"
            )
            full_context = self._intent_aware_compress(
                full_context, current_query, current_intent, self.max_tokens
            )
            estimated_tokens = self._estimate_tokens(full_context)
        
        return {
            "short_term": short_term,
            "medium_term": medium_term_text,
            "long_term": long_term_text,
            "current_intent": current_intent,
            "intent_confidence": intent_confidence,
            "conversation_phase": phase,
            "full_context": full_context,
            "estimated_tokens": estimated_tokens,
            "token_budgets": budgets,
            "topic_switches": state.topic_switch_count,
            "key_entities": state.key_entities
        }
    
    def _get_or_create_state(self, session_id: str) -> ConversationState:
        """获取或创建对话状态"""
        if session_id not in self._conversation_states:
            self._conversation_states[session_id] = ConversationState()
        return self._conversation_states[session_id]
    
    def _update_conversation_state(self, state: ConversationState, 
                                   query: str, intent: str, entities: List[str]):
        """更新对话状态"""
        # 检测话题转移
        if state.current_topic and intent != state.user_intent:
            # 意图变化可能表示话题转移
            if state.user_intent != "":
                state.topic_switch_count += 1
                state.previous_topic = state.current_topic
        
        state.current_topic = query[:50]
        state.user_intent = intent
        state.key_entities = list(set(state.key_entities + entities))[:20]
        state.accumulated_questions.append(query)
        
        # 只保留最近20个问题
        if len(state.accumulated_questions) > 20:
            state.accumulated_questions = state.accumulated_questions[-20:]
    
    def _detect_conversation_phase(self, state: ConversationState, 
                                   message_count: int) -> str:
        """检测对话阶段"""
        if message_count <= 2:
            return "opening"
        elif state.topic_switch_count > 0:
            return "transitioning"
        elif len(state.accumulated_questions) >= 10:
            return "closing"
        else:
            return "deepening"
    
    def _calculate_budgets(self, total_tokens: int, phase: str) -> Dict[str, int]:
        """根据对话阶段计算Token预算"""
        budget_ratios = self._token_budget_phases.get(phase, self._token_budget_phases["deepening"])
        return {
            "short_term": int(total_tokens * budget_ratios["short_term"]),
            "medium_term": int(total_tokens * budget_ratios["medium_term"]),
            "long_term": int(total_tokens * budget_ratios["long_term"]),
            "current_query": int(total_tokens * budget_ratios["current_query"])
        }
    
    def _extract_intent_aware_short_term(self, messages: List[Dict], 
                                         limit: int, current_intent: str,
                                         current_entities: List[str]) -> List[Dict]:
        """提取意图感知的短期上下文"""
        if len(messages) <= limit * 2:
            return messages
        
        # 获取最近的消息
        recent_messages = messages[-limit * 2:]
        
        # 为每条消息计算意图相关度分数
        scored_messages = []
        for msg in recent_messages:
            score = 0.0
            content = msg.get("content", "")
            
            # 意图匹配
            msg_intent, _ = self._intent_analyzer.analyze(content)
            if msg_intent == current_intent:
                score += 2.0
            
            # 实体重叠
            msg_entities = self._intent_analyzer.extract_entities(content)
            common_entities = set(current_entities) & set(msg_entities)
            score += len(common_entities) * 1.5
            
            # 时间衰减（越新的消息分数越高）
            score += 0.5
            
            scored_messages.append((score, msg))
        
        # 按分数排序，保留高相关度的消息
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # 保留top_k条，但保持时间顺序
        top_k = limit * 2
        selected = [msg for _, msg in scored_messages[:top_k]]
        
        # 按原始顺序排序
        selected.sort(key=lambda m: messages.index(m) if m in messages else 0)
        
        return selected
    
    def _get_intent_aware_summary(self, messages: List[Dict], 
                                  current_intent: str,
                                  current_entities: List[str],
                                  max_tokens: int) -> str:
        """获取意图感知的历史摘要"""
        # 生成缓存键（包含意图信息）
        cache_key = self._generate_intent_aware_key(messages, current_intent, current_entities)
        
        # 尝试从缓存获取
        cached = self._summary_cache.get(cache_key)
        if cached:
            app_logger.debug("意图感知摘要缓存命中")
            return cached
        
        # 生成新摘要（优先保留与当前意图相关的信息）
        summary = self._create_intent_aware_summary(messages, current_intent, current_entities, max_tokens)
        
        # 存入缓存
        self._summary_cache.put(cache_key, summary)
        
        return summary
    
    def _generate_intent_aware_key(self, messages: List[Dict], 
                                   intent: str, entities: List[str]) -> str:
        """生成意图感知的缓存键"""
        content = "|".join([
            f"{m.get('role', '')}:{m.get('content', '')[:100]}"
            for m in messages
        ])
        intent_info = f"{intent}:{','.join(sorted(entities))}"
        full_key = f"{content}|{intent_info}"
        return hashlib.sha256(full_key.encode()).hexdigest()[:16]
    
    def _create_intent_aware_summary(self, messages: List[Dict], 
                                     current_intent: str,
                                     current_entities: List[str],
                                     max_tokens: int) -> str:
        """创建意图感知的会话摘要"""
        if not messages:
            return ""
        
        # 分类信息（按意图相关性）
        relevant_info = []
        general_info = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            # 分析消息意图
            msg_intent, _ = self._intent_analyzer.analyze(content)
            msg_entities = self._intent_analyzer.extract_entities(content)
            
            # 检查与当前意图的相关性
            common_entities = set(current_entities) & set(msg_entities)
            is_relevant = (msg_intent == current_intent) or (len(common_entities) > 0)
            
            summary_line = f"{'用户' if role == 'user' else '助手'}: {content[:150]}"
            
            if is_relevant:
                relevant_info.append(summary_line)
            else:
                general_info.append(summary_line)
        
        # 优先保留相关信息
        summary_parts = ["【相关历史】"]
        summary_parts.extend(relevant_info[:10])
        
        if general_info:
            summary_parts.append("\n【其他背景】")
            summary_parts.extend(general_info[:5])
        
        summary_text = "\n".join(summary_parts)
        
        # 如果摘要太长，使用LLM进一步压缩
        if self._estimate_tokens(summary_text) > max_tokens:
            try:
                summary_prompt = f"""请将以下对话历史压缩为简洁摘要。

当前关注意图：{current_intent}
相关实体：{', '.join(current_entities)}

对话历史：
{summary_text[:2000]}

要求：
1. 优先保留与「{current_intent}」意图相关的信息
2. 保留重要的医疗实体信息
3. 控制在{max_tokens}个token内
4. 保持信息的准确性和完整性

请提供压缩后的摘要："""
                summary = llm_service.generate(
                    prompt=summary_prompt,
                    temperature=0.3,
                    max_tokens=max_tokens
                )
                return summary
            except Exception as e:
                app_logger.warning(f"创建意图感知摘要失败: {e}")
                return summary_text[:1000]
        
        return summary_text
    
    def _build_long_term_context(self, state: ConversationState, max_tokens: int) -> str:
        """构建长期上下文（用户画像和关键历史）"""
        parts = []
        
        # 关键实体
        if state.key_entities:
            parts.append(f"关注疾病/药物：{', '.join(state.key_entities[:10])}")
        
        # 话题转移历史
        if state.topic_switch_count > 0:
            parts.append(f"话题转移次数：{state.topic_switch_count}")
        
        # 累积问题主题
        if state.accumulated_questions:
            recent_questions = state.accumulated_questions[-5:]
            parts.append(f"近期关注：{' → '.join([q[:30] for q in recent_questions])}")
        
        long_term_text = "\n".join(parts)
        
        # 限制长度
        if self._estimate_tokens(long_term_text) > max_tokens:
            return long_term_text[:max_tokens * 2]
        
        return long_term_text
    
    def _build_intent_preservation_prompt(self, state: ConversationState, 
                                          current_intent: str) -> str:
        """构建意图保持提示"""
        prompts = []
        
        # 如果检测到话题转移，添加过渡提示
        if state.topic_switch_count > 0 and state.previous_topic:
            prompts.append(f"注意：用户话题已从「{state.previous_topic[:30]}...」转移到新话题。")
        
        # 添加当前意图提示
        intent_descriptions = {
            "symptom_inquiry": "用户正在咨询症状相关问题",
            "diagnosis_request": "用户希望了解可能的诊断方向",
            "treatment_inquiry": "用户正在询问治疗方案",
            "drug_inquiry": "用户正在咨询用药相关问题",
            "prevention_inquiry": "用户关注预防和注意事项",
            "lifestyle_inquiry": "用户询问生活方式相关建议",
            "follow_up": "用户进行后续追问",
            "emergency": "用户可能面临紧急情况",
            "general_inquiry": "用户进行一般性咨询"
        }
        
        intent_desc = intent_descriptions.get(current_intent, "用户进行咨询")
        prompts.append(f"意图识别：{intent_desc}")
        
        return "\n".join(prompts)
    
    def _combine_context_v2(self, short_term: str, medium_term: Optional[str],
                           long_term: Optional[str], current_query: str,
                           intent_preservation: str) -> str:
        """组合上下文 v2.0（带意图保持）"""
        context_parts = []
        
        # 意图保持提示（放在最前面，确保模型注意到）
        if intent_preservation:
            context_parts.append(f"【对话状态】\n{intent_preservation}\n")
        
        # 长期上下文
        if long_term:
            context_parts.append(f"【用户画像】\n{long_term}\n")
        
        # 中期上下文（会话摘要）
        if medium_term:
            context_parts.append(f"【历史摘要】\n{medium_term}\n")
        
        # 短期上下文（最近对话）
        if short_term:
            context_parts.append(f"【最近对话】\n{short_term}\n")
        
        # 当前查询
        context_parts.append(f"【当前问题】\n{current_query}")
        
        return "\n".join(context_parts)
    
    def _intent_aware_compress(self, context: str, current_query: str, 
                               current_intent: str, target_tokens: int) -> str:
        """意图感知的智能压缩"""
        current_tokens = self._estimate_tokens(context)
        
        if current_tokens <= target_tokens:
            return context
        
        # 策略1: 使用上下文压缩器（意图感知）
        try:
            from app.services.context_compressor import context_compressor
            compressed = context_compressor.compress(context, current_query, target_tokens)
            if self._estimate_tokens(compressed) <= target_tokens:
                return compressed
        except Exception:
            pass
        
        # 策略2: 保留意图相关部分，压缩其他部分
        sections = context.split("\n【")
        preserved_sections = []
        compressed_sections = []
        
        for section in sections:
            if not section.strip():
                continue
            
            # 判断是否与当前意图高度相关
            section_lower = section.lower()
            is_critical = any(keyword in section_lower for keyword in ["对话状态", "当前问题"])
            is_relevant = self._is_intent_relevant(section, current_intent)
            
            if is_critical or is_relevant:
                preserved_sections.append(section)
            else:
                compressed_sections.append(section)
        
        # 先保留关键部分
        result = "\n【".join(preserved_sections)
        result_tokens = self._estimate_tokens(result)
        
        # 如果还有空间，逐步添加压缩后的部分
        if result_tokens < target_tokens * 0.9:
            remaining_budget = target_tokens - result_tokens
            for section in compressed_sections:
                section_tokens = self._estimate_tokens(section)
                if section_tokens > remaining_budget:
                    # 简单截断
                    truncated = section[:int(remaining_budget * 2)]
                    result += "\n【" + truncated + "...（已压缩）"
                    break
                result += "\n【" + section
                remaining_budget -= section_tokens
        
        return result
    
    def _is_intent_relevant(self, text: str, intent: str) -> bool:
        """判断文本是否与意图相关"""
        text_intent, confidence = self._intent_analyzer.analyze(text)
        return text_intent == intent and confidence > 0.3
    
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
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量"""
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
    
    def detect_topic_switch(self, session_id: str, new_query: str) -> bool:
        """检测话题是否发生转移"""
        state = self._get_or_create_state(session_id)
        new_intent, _ = self._intent_analyzer.analyze(new_query)
        
        # 如果意图发生显著变化，认为话题转移
        if state.user_intent and new_intent != state.user_intent:
            # 排除 follow_up 意图（追问不算话题转移）
            if new_intent != "follow_up" and state.user_intent != "follow_up":
                return True
        
        return False
    
    def clear_session(self, session_id: str):
        """清空指定会话的状态和缓存"""
        if session_id in self._conversation_states:
            del self._conversation_states[session_id]
        self._summary_cache.clear()
        app_logger.info(f"会话 {session_id} 的上下文状态已清空")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        state = self._conversation_states.get(session_id)
        if not state:
            return {"error": "会话不存在"}
        
        return {
            "current_topic": state.current_topic,
            "current_intent": state.user_intent,
            "topic_switches": state.topic_switch_count,
            "key_entities": state.key_entities,
            "question_count": len(state.accumulated_questions),
            "cache_stats": {
                "max_size": self._summary_cache._max_size,
                "current_size": len(self._summary_cache._cache)
            }
        }


# 全局实例（v2.0）
context_manager = ContextManagerV2()

# 保持向后兼容
from .context_manager_legacy import ContextManager as ContextManagerV1
context_manager_v1 = ContextManagerV1()
