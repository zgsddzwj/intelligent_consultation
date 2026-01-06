"""Agent基类"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from app.services.llm_service import llm_service
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
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool.execute(**kwargs)
        raise ValueError(f"工具 {tool_name} 不存在")
    
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

