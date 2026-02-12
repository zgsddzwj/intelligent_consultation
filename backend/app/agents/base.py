"""Agent基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.services.llm_service import llm_service
from app.services.langfuse_service import langfuse_service
from app.utils.logger import app_logger
import time


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm = llm_service
        self.tools: List[Any] = []
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        pass
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入并返回结果"""
        pass
    
    def add_tool(self, tool: Any):
        """添加工具"""
        self.tools.append(tool)
        app_logger.info(f"Agent {self.name} 添加工具: {tool.name}")
    
    def execute_tool(self, tool_name: str, trace_id: Optional[str] = None,
                     parent_observation_id: Optional[str] = None, **kwargs) -> Any:
        """执行工具（带Langfuse追踪）"""
        # 创建工具调用的span
        span = None
        if langfuse_service.enabled:
            span = langfuse_service.span(
                name=f"tool.{tool_name}",
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
                metadata={
                    "agent": self.name,
                    "tool": tool_name,
                    "parameters": {k: str(v)[:100] for k, v in kwargs.items()}  # 限制长度
                }
            )
            parent_observation_id = span.id if span and hasattr(span, 'id') else parent_observation_id
        
        start_time = time.time()
        
        try:
            for tool in self.tools:
                if tool.name == tool_name:
                    result = tool.execute(**kwargs)
                    
                    # 记录工具执行成功
                    if langfuse_service.enabled and span:
                        # 更新span metadata
                        try:
                            span.end(metadata={
                                "success": True,
                                "execution_time": time.time() - start_time,
                                "result_size": len(str(result))
                            })
                        except:
                            pass
                    
                    return result
            
            raise ValueError(f"工具 {tool_name} 不存在")
            
        except Exception as e:
            # 记录工具执行失败
            if langfuse_service.enabled and span:
                try:
                    span.end(metadata={
                        "success": False,
                        "error": str(e),
                        "execution_time": time.time() - start_time
                    })
                except:
                    pass
            
            raise
    
    def log_execution(self, input_data: Dict, output_data: Dict, 
                     execution_time: float, tools_used: List[str] = None):
        """记录执行日志"""
        log_data = {
            "agent_name": self.name,
            "input": input_data,
            "output": output_data,
            "execution_time": f"{execution_time:.3f}s",
            "tools_used": tools_used or []
        }
        app_logger.info(f"Agent执行日志: {log_data}")
        return log_data
    
    def format_answer_with_fallback(self, answer: str, context: str) -> str:
        """
        格式化回答，如果没有找到上下文则添加提示
        """
        no_result_hints = ["未找到相关医疗文献", "未找到相关知识库结果"]
        
        # 检查上下文是否为空或包含无结果提示
        has_context = bool(context and context.strip())
        is_empty_result = any(hint in context for hint in no_result_hints) if has_context else True
        
        if not has_context or is_empty_result:
            fallback_hint = "\n\n（未找到相关知识库结果，以上回答仅基于模型通用知识，仅供参考。）"
            if fallback_hint not in answer:
                return answer.rstrip() + fallback_hint
        
        return answer

