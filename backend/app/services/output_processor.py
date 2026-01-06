"""输出后处理 - 格式化、术语标准化和质量评分"""
from typing import Dict, List, Any, Optional
import re
from app.utils.logger import app_logger


class OutputProcessor:
    """输出后处理器"""
    
    def __init__(self):
        # 医疗术语标准化映射
        self.term_mapping = {
            "高血压": "高血压病",
            "糖尿病": "糖尿病",
            "心脏病": "心血管疾病",
            # 可以扩展更多术语映射
        }
    
    def process(self, answer: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理LLM输出
        
        Args:
            answer: 原始回答
            metadata: 元数据
        
        Returns:
            处理后的结果，包含：
                - formatted_answer: 格式化后的回答
                - standardized_answer: 术语标准化后的回答
                - quality_score: 质量评分
                - issues: 发现的问题
        """
        result = {
            "original_answer": answer,
            "formatted_answer": "",
            "standardized_answer": "",
            "quality_score": 0.0,
            "issues": []
        }
        
        try:
            # 1. 格式化
            formatted = self._format_answer(answer)
            result["formatted_answer"] = formatted
            
            # 2. 术语标准化
            standardized = self._standardize_terms(formatted)
            result["standardized_answer"] = standardized
            
            # 3. 质量评分
            quality_score, issues = self._score_quality(standardized, metadata)
            result["quality_score"] = quality_score
            result["issues"] = issues
            
            # 4. 敏感信息过滤
            filtered = self._filter_sensitive_info(standardized)
            result["filtered_answer"] = filtered
            
        except Exception as e:
            app_logger.error(f"输出处理失败: {e}")
            result["error"] = str(e)
            result["formatted_answer"] = answer
            result["standardized_answer"] = answer
        
        return result
    
    def _format_answer(self, answer: str) -> str:
        """格式化回答"""
        # 1. 去除多余空白
        answer = re.sub(r'\s+', ' ', answer)
        answer = answer.strip()
        
        # 2. 确保段落分隔
        answer = re.sub(r'([。！？])([^\s])', r'\1\n\n\2', answer)
        
        # 3. 格式化列表
        # 检测编号列表
        answer = re.sub(r'(\d+)[\.、]\s*', r'\1. ', answer)
        
        # 4. 格式化引用
        answer = re.sub(r'\[来源(\d+)\]', r'[来源\1]', answer)
        
        return answer
    
    def _standardize_terms(self, answer: str) -> str:
        """标准化医疗术语"""
        standardized = answer
        
        for old_term, new_term in self.term_mapping.items():
            # 使用单词边界确保完整匹配
            pattern = r'\b' + re.escape(old_term) + r'\b'
            standardized = re.sub(pattern, new_term, standardized)
        
        return standardized
    
    def _score_quality(self, answer: str, metadata: Optional[Dict] = None) -> tuple[float, List[str]]:
        """评分回答质量"""
        score = 1.0
        issues = []
        
        # 1. 检查长度
        if len(answer) < 50:
            score -= 0.2
            issues.append("回答过短")
        elif len(answer) > 5000:
            score -= 0.1
            issues.append("回答过长")
        
        # 2. 检查是否有来源标注
        has_source = bool(re.search(r'\[来源\d+\]|来源[：:]\d+', answer))
        if not has_source and metadata and metadata.get("has_sources"):
            score -= 0.3
            issues.append("缺少来源标注")
        
        # 3. 检查是否有免责声明
        has_disclaimer = "仅供参考" in answer or "不替代" in answer
        if not has_disclaimer:
            score -= 0.1
            issues.append("缺少免责声明")
        
        # 4. 检查是否有过于肯定的表述（可能有问题）
        overconfident_patterns = ["一定", "必须", "肯定", "绝对"]
        overconfident_count = sum(1 for pattern in overconfident_patterns if pattern in answer)
        if overconfident_count > 3:
            score -= 0.2
            issues.append("包含过多过于肯定的表述")
        
        # 5. 检查结构完整性
        has_structure = bool(re.search(r'[1-9][\.、]|•|·', answer))
        if not has_structure and len(answer) > 200:
            score -= 0.1
            issues.append("缺少结构化格式")
        
        # 确保分数在0-1之间
        score = max(0.0, min(1.0, score))
        
        return score, issues
    
    def _filter_sensitive_info(self, answer: str) -> str:
        """过滤敏感信息"""
        filtered = answer
        
        # 1. 过滤可能的个人信息（如电话号码、身份证号等）
        # 电话号码
        filtered = re.sub(r'\d{3}-\d{4}-\d{4}|\d{11}', '[电话]', filtered)
        # 身份证号
        filtered = re.sub(r'\d{17}[\dXx]', '[身份证]', filtered)
        
        # 2. 可以添加更多敏感信息过滤规则
        
        return filtered


# 全局实例
output_processor = OutputProcessor()

