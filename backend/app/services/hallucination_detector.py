"""幻觉检测器 - 事实一致性检查和来源验证"""
from typing import Dict, List, Any, Optional
import re
from app.services.llm_service import llm_service
from app.utils.logger import app_logger
from app.config import get_settings

settings = get_settings()


class HallucinationDetector:
    """幻觉检测器"""
    
    def __init__(self):
        self.verification_prompt_template = """请验证以下陈述是否与提供的上下文信息一致。

上下文信息：
{context}

需要验证的陈述：
{claim}

请回答：
1. 该陈述是否与上下文一致？（是/否/不确定）
2. 如果不一致，请指出不一致的地方
3. 该陈述是否有明确的来源支持？（是/否）

请以JSON格式回答：
{{
    "consistent": true/false/null,
    "has_source": true/false,
    "inconsistency": "不一致的地方（如果存在）",
    "confidence": 0.0-1.0
}}"""
    
    def detect(self, answer: str, context: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        检测回答中的幻觉
        
        Args:
            answer: LLM生成的回答
            context: 用于生成回答的上下文
            sources: 来源列表
        
        Returns:
            检测结果字典
        """
        result = {
            "has_hallucination": False,
            "confidence": 1.0,
            "issues": [],
            "unverified_claims": [],
            "missing_sources": []
        }
        
        try:
            # 1. 检查是否有来源标注
            source_issues = self._check_source_annotation(answer, sources or [])
            if source_issues:
                result["issues"].extend(source_issues)
                result["missing_sources"] = source_issues
                result["has_hallucination"] = True
                result["confidence"] = min(result["confidence"], 0.7)
            
            # 2. 提取关键陈述
            claims = self._extract_claims(answer)
            
            # 3. 验证每个关键陈述
            for claim in claims:
                verification = self._verify_claim(claim, context)
                
                if not verification.get("consistent"):
                    result["has_hallucination"] = True
                    result["unverified_claims"].append({
                        "claim": claim,
                        "verification": verification
                    })
                    result["confidence"] = min(result["confidence"], verification.get("confidence", 0.5))
                    
                    if verification.get("inconsistency"):
                        result["issues"].append({
                            "type": "inconsistency",
                            "claim": claim,
                            "issue": verification["inconsistency"]
                        })
            
            # 4. 检查是否有"编造"的迹象
            fabrication_signals = self._detect_fabrication_signals(answer, context)
            if fabrication_signals:
                result["has_hallucination"] = True
                result["issues"].extend(fabrication_signals)
                result["confidence"] = min(result["confidence"], 0.6)
            
        except Exception as e:
            app_logger.error(f"幻觉检测失败: {e}")
            result["error"] = str(e)
        
        return result
    
    def _check_source_annotation(self, answer: str, sources: List[str]) -> List[str]:
        """检查回答中的来源标注"""
        issues = []
        
        # 检查是否包含来源引用
        source_patterns = [
            r"来源[：:]\s*\d+",
            r"参考[：:]\s*\d+",
            r"\[来源\d+\]",
            r"\(来源\d+\)",
            r"根据.*?文献",
            r"根据.*?研究"
        ]
        
        has_source_annotation = any(re.search(pattern, answer) for pattern in source_patterns)
        
        # 如果提供了来源但没有标注
        if sources and not has_source_annotation:
            # 检查是否包含关键医疗信息（应该标注来源）
            medical_keywords = ["诊断", "治疗", "药物", "剂量", "症状", "疾病", "检查"]
            has_medical_info = any(keyword in answer for keyword in medical_keywords)
            
            if has_medical_info:
                issues.append("回答包含医疗信息但未标注来源")
        
        return issues
    
    def _extract_claims(self, answer: str) -> List[str]:
        """提取回答中的关键陈述"""
        claims = []
        
        # 按句子分割
        sentences = re.split(r'[。！？\n]', answer)
        
        # 过滤掉太短的句子和免责声明
        medical_keywords = ["诊断", "治疗", "药物", "剂量", "症状", "疾病", "检查", "建议", "可能"]
        disclaimer_keywords = ["仅供参考", "不替代", "遵医嘱", "建议就医"]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # 跳过免责声明
            if any(keyword in sentence for keyword in disclaimer_keywords):
                continue
            
            # 包含医疗关键词的句子可能是关键陈述
            if any(keyword in sentence for keyword in medical_keywords):
                claims.append(sentence)
        
        return claims[:10]  # 最多检查10个陈述
    
    def _verify_claim(self, claim: str, context: str) -> Dict[str, Any]:
        """验证单个陈述是否与上下文一致"""
        try:
            prompt = self.verification_prompt_template.format(
                context=context[:2000],  # 限制上下文长度
                claim=claim
            )
            
            # 使用LLM进行验证
            response = llm_service.generate(
                prompt=prompt,
                temperature=0.3,  # 低temperature以获得更确定的结果
                max_tokens=500
            )
            
            # 尝试解析JSON响应
            import json
            # 提取JSON部分
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                verification = json.loads(json_match.group())
                return verification
            else:
                # 如果无法解析JSON，进行简单判断
                if "一致" in response or "consistent" in response.lower():
                    return {"consistent": True, "confidence": 0.7}
                elif "不一致" in response or "inconsistent" in response.lower():
                    return {"consistent": False, "confidence": 0.7}
                else:
                    return {"consistent": None, "confidence": 0.5}
                    
        except Exception as e:
            app_logger.warning(f"验证陈述失败: {e}")
            return {"consistent": None, "confidence": 0.5, "error": str(e)}
    
    def _detect_fabrication_signals(self, answer: str, context: str) -> List[Dict[str, str]]:
        """检测编造的迹象"""
        issues = []
        
        # 1. 检查是否包含过于具体的数字（可能编造）
        specific_numbers = re.findall(r'\d+\.\d+%|\d+mg|\d+ml|\d+次/天', answer)
        if specific_numbers and not any(str(num) in context for num in specific_numbers):
            issues.append({
                "type": "specific_number_without_source",
                "message": f"回答包含具体数字但上下文中未找到: {specific_numbers[:3]}"
            })
        
        # 2. 检查是否包含过于肯定的表述（可能编造）
        strong_assertions = ["一定", "必须", "肯定", "绝对", "确定"]
        if any(assertion in answer for assertion in strong_assertions):
            # 检查上下文中是否有支持
            if "不确定" not in context and "可能" not in context:
                issues.append({
                    "type": "overconfident_assertion",
                    "message": "回答包含过于肯定的表述，但上下文未提供充分支持"
                })
        
        # 3. 检查是否包含上下文未提及的疾病/药物名称
        # 这里可以扩展为更复杂的实体识别
        
        return issues
    
    def add_source_warnings(self, answer: str, detection_result: Dict[str, Any]) -> str:
        """在回答中添加来源警告"""
        if not detection_result.get("has_hallucination"):
            return answer
        
        warnings = []
        
        # 添加未标注来源的警告
        if detection_result.get("missing_sources"):
            warnings.append("⚠️ 注意：部分信息未标注来源，请谨慎参考。")
        
        # 添加未验证陈述的警告
        if detection_result.get("unverified_claims"):
            warnings.append("⚠️ 注意：部分陈述无法在提供的上下文中验证，建议咨询专业医生。")
        
        if warnings:
            answer += "\n\n" + "\n".join(warnings)
        
        return answer


# 全局实例
hallucination_detector = HallucinationDetector()

