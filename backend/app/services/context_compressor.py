"""上下文压缩技术 - 使用LLM进行摘要和关键信息保留"""
from typing import Dict, List, Any, Optional
from app.services.llm_service import llm_service
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class ContextCompressor:
    """上下文压缩器"""
    
    def __init__(self):
        self.compression_ratio = 0.3  # 压缩到30%
        self.medical_keywords = [
            "症状", "诊断", "疾病", "治疗", "药物", "剂量", "检查",
            "高血压", "糖尿病", "心脏病", "癌症", "感染", "炎症",
            "手术", "用药", "副作用", "禁忌", "适应症"
        ]
    
    def compress(self, context: str, current_query: str, 
                 target_tokens: Optional[int] = None) -> str:
        """
        压缩上下文
        
        Args:
            context: 原始上下文
            current_query: 当前查询（用于保留相关信息）
            target_tokens: 目标token数
        
        Returns:
            压缩后的上下文
        """
        if not target_tokens:
            target_tokens = int(len(context) // 2 * self.compression_ratio)
        
        try:
            # 1. 提取关键信息
            key_info = self._extract_key_information(context, current_query)
            
            # 2. 使用LLM进行摘要
            summary = self._llm_summarize(context, current_query, target_tokens)
            
            # 3. 合并关键信息和摘要
            compressed = self._merge_key_info_and_summary(key_info, summary, current_query)
            
            return compressed
            
        except Exception as e:
            app_logger.warning(f"上下文压缩失败，使用简化版本: {e}")
            # 降级：简单截取
            return self._simple_truncate(context, target_tokens)
    
    def _extract_key_information(self, context: str, query: str) -> Dict[str, List[str]]:
        """提取关键信息"""
        key_info = {
            "symptoms": [],
            "diagnoses": [],
            "medications": [],
            "examinations": [],
            "other": []
        }
        
        # 按句子分割
        sentences = context.split('。')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 检查是否包含医疗关键词
            has_medical_keyword = any(keyword in sentence for keyword in self.medical_keywords)
            
            # 检查是否与查询相关
            query_keywords = set(query.lower().split())
            sentence_keywords = set(sentence.lower().split())
            is_relevant = len(query_keywords & sentence_keywords) > 0
            
            if has_medical_keyword or is_relevant:
                # 简单分类
                if any(kw in sentence for kw in ["症状", "表现", "感觉"]):
                    key_info["symptoms"].append(sentence)
                elif any(kw in sentence for kw in ["诊断", "疾病", "病"]):
                    key_info["diagnoses"].append(sentence)
                elif any(kw in sentence for kw in ["药物", "用药", "药"]):
                    key_info["medications"].append(sentence)
                elif any(kw in sentence for kw in ["检查", "检验", "检测"]):
                    key_info["examinations"].append(sentence)
                else:
                    key_info["other"].append(sentence)
        
        return key_info
    
    def _llm_summarize(self, context: str, query: str, target_tokens: int) -> str:
        """使用LLM进行摘要"""
        try:
            summary_prompt = f"""请将以下对话上下文压缩为简洁摘要，保留与当前问题相关的关键医疗信息。

当前问题：{query}

对话上下文：
{context[:3000]}  # 限制长度

要求：
1. 保留与当前问题相关的信息
2. 保留重要的医疗信息（症状、诊断、用药、检查等）
3. 压缩到约{target_tokens}个token
4. 保持信息的准确性和完整性

请提供压缩后的摘要："""
            
            summary = llm_service.generate(
                prompt=summary_prompt,
                temperature=0.3,  # 低temperature以获得更准确的摘要
                max_tokens=min(target_tokens, 1000)
            )
            
            return summary
            
        except Exception as e:
            app_logger.warning(f"LLM摘要失败: {e}")
            return ""
    
    def _merge_key_info_and_summary(self, key_info: Dict[str, List[str]], 
                                    summary: str, query: str) -> str:
        """合并关键信息和摘要"""
        parts = []
        
        # 添加摘要
        if summary:
            parts.append(f"上下文摘要：\n{summary}\n")
        
        # 添加关键信息（如果摘要中没有）
        if key_info["symptoms"]:
            parts.append(f"症状信息：{'；'.join(key_info['symptoms'][:3])}\n")
        if key_info["diagnoses"]:
            parts.append(f"诊断信息：{'；'.join(key_info['diagnoses'][:3])}\n")
        if key_info["medications"]:
            parts.append(f"用药信息：{'；'.join(key_info['medications'][:3])}\n")
        
        # 添加当前查询
        parts.append(f"\n当前问题：{query}")
        
        return "\n".join(parts)
    
    def _simple_truncate(self, context: str, target_tokens: int) -> str:
        """简单截取（降级方案）"""
        target_chars = target_tokens * 2  # 粗略估算
        
        if len(context) <= target_chars:
            return context
        
        # 保留开头和结尾
        head_chars = target_chars // 2
        tail_chars = target_chars - head_chars
        
        return context[:head_chars] + "\n...\n" + context[-tail_chars:]


# 全局实例
context_compressor = ContextCompressor()

