"""运营Agent"""
from typing import Dict, Any, List
import time
from app.agents.base import BaseAgent
from app.utils.logger import app_logger


class OperationsAgent(BaseAgent):
    """运营Agent - 数据分析、系统监控、知识库优化建议"""
    
    def __init__(self):
        super().__init__(
            name="operations",
            description="运营分析Agent，提供数据分析、系统监控、优化建议"
        )
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return """你是一位专业的运营分析AI。你的职责是：
1. 分析咨询数据和系统使用情况
2. 监控系统性能指标
3. 提供知识库优化建议
4. 生成运营报告
5. 识别系统改进机会"""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理运营分析请求"""
        start_time = time.time()
        
        try:
            request_type = input_data.get("type", "analysis")  # analysis, monitoring, optimization
            
            app_logger.info(f"运营Agent处理请求: {request_type}")
            
            if request_type == "analysis":
                result = self._analyze_data(input_data.get("data", {}))
            elif request_type == "monitoring":
                result = self._monitor_system(input_data.get("metrics", {}))
            elif request_type == "optimization":
                result = self._suggest_optimization(input_data.get("context", {}))
            else:
                result = self._generate_report(input_data)
            
            execution_time = time.time() - start_time
            self.log_execution(input_data, result, execution_time, [])
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            app_logger.error(f"运营Agent处理失败: {e}")
            execution_time = time.time() - start_time
            return {
                "answer": f"处理请求时发生错误: {str(e)}",
                "error": str(e),
                "execution_time": execution_time
            }
    
    def _analyze_data(self, data: Dict) -> Dict[str, Any]:
        """分析数据"""
        prompt = f"""请分析以下运营数据：

{data}

请提供：
1. 关键指标总结
2. 趋势分析
3. 异常情况识别
4. 改进建议"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "data_analysis"
        }
    
    def _monitor_system(self, metrics: Dict) -> Dict[str, Any]:
        """监控系统"""
        prompt = f"""请分析以下系统监控指标：

{metrics}

请提供：
1. 系统健康状态评估
2. 性能指标分析
3. 潜在问题识别
4. 优化建议"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "system_monitoring"
        }
    
    def _suggest_optimization(self, context: Dict) -> Dict[str, Any]:
        """提供优化建议"""
        prompt = f"""基于以下上下文，提供知识库和系统优化建议：

{context}

请提供：
1. 知识库内容优化建议
2. 检索效果改进方案
3. Agent性能优化建议
4. 用户体验改进建议"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "optimization_suggestion"
        }
    
    def _generate_report(self, input_data: Dict) -> Dict[str, Any]:
        """生成运营报告"""
        prompt = f"""请生成运营报告：

{input_data}

报告应包括：
1. 数据概览
2. 关键指标
3. 趋势分析
4. 问题与建议"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "report"
        }

