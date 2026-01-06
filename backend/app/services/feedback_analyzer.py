"""反馈分析系统"""
from typing import Dict, List, Any, Optional
from app.utils.logger import app_logger
from app.services.langfuse_service import langfuse_service


class FeedbackAnalyzer:
    """反馈分析器"""
    
    def __init__(self):
        self.positive_keywords = ["好", "有用", "准确", "专业", "满意", "帮助"]
        self.negative_keywords = ["错误", "不准确", "没用", "不满意", "差", "问题"]
    
    def analyze(self, rating: int, comment: Optional[str] = None,
                helpful: Optional[bool] = None) -> Dict[str, Any]:
        """
        分析用户反馈
        
        Args:
            rating: 评分（1-5）
            comment: 评论
            helpful: 是否有帮助
        
        Returns:
            分析结果
        """
        analysis = {
            "sentiment": "neutral",
            "key_issues": [],
            "suggestions": [],
            "priority": "low"
        }
        
        # 1. 情感分析
        if rating >= 4:
            analysis["sentiment"] = "positive"
        elif rating <= 2:
            analysis["sentiment"] = "negative"
            analysis["priority"] = "high"
        else:
            analysis["sentiment"] = "neutral"
        
        # 2. 评论分析
        if comment:
            comment_lower = comment.lower()
            
            # 提取关键词
            positive_count = sum(1 for kw in self.positive_keywords if kw in comment_lower)
            negative_count = sum(1 for kw in self.negative_keywords if kw in comment_lower)
            
            if negative_count > positive_count:
                analysis["sentiment"] = "negative"
                analysis["priority"] = "high"
            elif positive_count > negative_count:
                analysis["sentiment"] = "positive"
            
            # 提取问题
            if "不准确" in comment or "错误" in comment:
                analysis["key_issues"].append("准确性")
            if "慢" in comment or "延迟" in comment:
                analysis["key_issues"].append("响应速度")
            if "不理解" in comment or "不清楚" in comment:
                analysis["key_issues"].append("可理解性")
        
        # 3. 生成建议
        if analysis["sentiment"] == "negative":
            if "准确性" in analysis["key_issues"]:
                analysis["suggestions"].append("检查RAG检索结果和知识图谱数据")
            if "响应速度" in analysis["key_issues"]:
                analysis["suggestions"].append("优化缓存和并行处理")
            if "可理解性" in analysis["key_issues"]:
                analysis["suggestions"].append("优化Prompt和输出格式")
        
        return analysis
    
    def get_feedback_stats(self, trace_ids: List[str]) -> Dict[str, Any]:
        """获取反馈统计（从Langfuse）"""
        # 这里可以从Langfuse API获取统计数据
        # 简化实现
        return {
            "total_feedback": 0,
            "average_rating": 0.0,
            "positive_rate": 0.0,
            "negative_rate": 0.0
        }


# 全局实例
feedback_analyzer = FeedbackAnalyzer()

