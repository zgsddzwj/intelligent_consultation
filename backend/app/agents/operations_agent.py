"""运营Agent"""
from typing import Dict, Any, List
import time
from app.agents.base import BaseAgent
from app.prompts import OperationsPrompts
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
        return OperationsPrompts.SYSTEM
    
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
        prompt = OperationsPrompts.format_data_analysis(str(data))
        
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
        prompt = OperationsPrompts.format_system_monitoring(str(metrics))
        
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
        prompt = OperationsPrompts.format_optimization(str(context))
        
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
        prompt = OperationsPrompts.format_report(str(input_data))
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "report"
        }

