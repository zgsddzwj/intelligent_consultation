"""Agent基类模块

提供所有Agent的抽象基类，定义统一的接口和通用功能：
- 工具管理（注册、执行、追踪）
- LLM调用封装（带重试和缓存）
- 执行日志记录
- Langfuse可观测性集成
- 回答格式化和降级处理
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from app.services.llm_service import llm_service
from app.services.langfuse_service import langfuse_service
from app.utils.logger import app_logger
import time


class BaseAgent(ABC):
    """Agent抽象基类
    
    所有专业Agent（医生、健康管家、客服、运营）的基类，
    提供统一的工具管理、LLM调用和可观测性能力。
    
    Attributes:
        name: Agent名称标识
        description: Agent功能描述
        llm: LLM服务实例
        tools: 已注册的工具列表
        version: Agent版本号
        stats: 执行统计信息
    
    Example:
        >>> class MyAgent(BaseAgent):
        ...     def __init__(self):
        ...         super().__init__("my_agent", "示例Agent")
        ...     def get_system_prompt(self) -> str:
        ...         return "你是一个有用的助手"
        ...     def process(self, input_data: Dict) -> Dict:
        ...         return {"answer": "处理完成"}
    """
    
    # 类级别的统计信息
    _stats: Dict[str, Dict] = {}
    
    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        """
        初始化Agent实例
        
        Args:
            name: Agent唯一名称标识
            description: Agent的功能描述
            version: Agent版本号，默认1.0.0
        """
        self.name = name
        self.description = description
        self.version = version
        self.llm = llm_service
        self.tools: List[Any] = []
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_execution_time": 0.0,
            "tools_usage": {}
        }
        
        # 初始化类级别统计
        if name not in BaseAgent._stats:
            BaseAgent._stats[name] = {
                "instance_calls": 0,
                "last_called": None
            }
        
        app_logger.info(f"Agent初始化: {name} v{version} - {description}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取Agent的系统Prompt
        
        Returns:
            系统Prompt字符串，用于设置LLM的角色和行为约束
        """
        pass
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户输入并返回结果
        
        这是Agent的核心方法，每个子类必须实现具体的业务逻辑。
        
        Args:
            input_data: 输入数据字典，通常包含：
                - question: 用户问题
                - context: 上下文信息
                - type: 咨询类型
                - trace_id: 追踪ID
        
        Returns:
            结果字典，通常包含：
                - answer: 生成的回答
                - sources: 信息来源列表
                - risk_level: 风险等级（可选）
                - tools_used: 使用的工具列表
                - execution_time: 执行时间
        """
        pass
    
    def add_tool(self, tool: Any) -> None:
        """注册工具到Agent
        
        Args:
            tool: 工具实例，必须具有name属性和execute方法
        """
        # 验证工具接口
        if not hasattr(tool, 'name'):
            raise ValueError(f"工具缺少name属性: {type(tool)}")
        if not hasattr(tool, 'execute') or not callable(getattr(tool, 'execute')):
            raise ValueError(f"工具缺少execute方法: {tool.name}")
        
        # 检查重复注册
        existing_names = [t.name for t in self.tools]
        if tool.name in existing_names:
            app_logger.warning(f"Agent {self.name}: 工具 {tool.name} 已存在，将被替换")
            self.tools = [t for t in self.tools if t.name != tool.name]
        
        self.tools.append(tool)
        app_logger.debug(f"Agent {self.name} 注册工具: {tool.name}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """移除已注册的工具
        
        Args:
            tool_name: 要移除的工具名称
            
        Returns:
            是否成功移除
        """
        original_len = len(self.tools)
        self.tools = [t for t in self.tools if t.name != tool_name]
        removed = len(self.tools) < original_len
        if removed:
            app_logger.debug(f"Agent {self.name} 移除工具: {tool_name}")
        return removed
    
    def get_tool(self, tool_name: str) -> Any:
        """获取指定工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具实例，如果不存在则返回None
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有已注册的工具
        
        Returns:
            工具信息列表，包含name和description
        """
        return [
            {"name": t.name, "description": getattr(t, 'description', '')}
            for t in self.tools
        ]
    
    def execute_tool(self, tool_name: str, trace_id: Optional[str] = None,
                     parent_observation_id: Optional[str] = None, **kwargs) -> Any:
        """执行指定工具（带Langfuse追踪和错误处理）
        
        Args:
            tool_name: 要执行的工具名称
            trace_id: Langfuse追踪ID
            parent_observation_id: 父级观察ID（用于构建追踪层级）
            **kwargs: 传递给工具的参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 工具不存在时抛出
            Exception: 工具执行失败时抛出原始异常
        """
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
                    "parameters": {k: str(v)[:100] for k, v in kwargs.items()}
                }
            )
            parent_observation_id = span.id if span and hasattr(span, 'id') else parent_observation_id
        
        start_time = time.time()
        
        try:
            for tool in self.tools:
                if tool.name == tool_name:
                    result = tool.execute(**kwargs)
                    
                    # 更新工具使用统计
                    tool_key = f"{self.name}.{tool_name}"
                    self.stats["tools_usage"][tool_key] = \
                        self.stats["tools_usage"].get(tool_key, 0) + 1
                    
                    # 记录工具执行成功
                    if langfuse_service.enabled and span:
                        try:
                            span.end(metadata={
                                "success": True,
                                "execution_time": time.time() - start_time,
                                "result_size": len(str(result))
                            })
                        except Exception:
                            pass
                    
                    return result
            
            raise ValueError(f"工具 '{tool_name}' 在Agent '{self.name}' 中不存在。可用工具: {[t.name for t in self.tools]}")
            
        except Exception as e:
            # 记录工具执行失败
            if langfuse_service.enabled and span:
                try:
                    span.end(metadata={
                        "success": False,
                        "error": str(e)[:500],
                        "execution_time": time.time() - start_time
                    })
                except Exception:
                    pass
            raise
    
    def log_execution(self, input_data: Dict, output_data: Dict, 
                     execution_time: float, tools_used: List[str] = None) -> Dict:
        """记录执行日志并更新统计信息
        
        Args:
            input_data: 输入数据
            output_data: 输出数据
            execution_time: 执行耗时（秒）
            tools_used: 使用的工具名称列表
            
        Returns:
            完整的日志数据字典
        """
        # 更新统计
        self.stats["total_calls"] += 1
        self.stats["total_execution_time"] += execution_time
        
        if output_data.get("error"):
            self.stats["failed_calls"] += 1
        else:
            self.stats["successful_calls"] += 1
        
        # 更新类级别统计
        BaseAgent._stats[self.name]["instance_calls"] += 1
        BaseAgent._stats[self.name]["last_called"] = time.isoformat(time.localtime())
        
        log_data = {
            "agent_name": self.name,
            "agent_version": self.version,
            "input_summary": {
                "question_length": len(str(input_data.get("question", ""))),
                "type": input_data.get("type", "unknown")
            },
            "output_summary": {
                "answer_length": len(str(output_data.get("answer", ""))),
                "has_error": bool(output_data.get("error"))
            },
            "execution_time": round(execution_time, 3),
            "tools_used": tools_used or [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        app_logger.info(f"[{self.name}] 执行完成: {log_data['execution_time']}s, 工具: {log_data['tools_used']}")
        return log_data
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Agent执行统计信息
        
        Returns:
            统计信息字典，包含调用次数、成功率、平均耗时等
        """
        total = self.stats["total_calls"]
        avg_time = (self.stats["total_execution_time"] / total) if total > 0 else 0
        success_rate = (self.stats["successful_calls"] / total * 100) if total > 0 else 0
        
        return {
            "agent": self.name,
            "version": self.version,
            "total_calls": total,
            "successful_calls": self.stats["successful_calls"],
            "failed_calls": self.stats["failed_calls"],
            "success_rate": round(success_rate, 2),
            "avg_execution_time": round(avg_time, 3),
            "total_execution_time": round(self.stats["total_execution_time"], 3),
            "tools_registered": len(self.tools),
            "tools_usage": dict(self.stats["tools_usage"])
        }
    
    def format_answer_with_fallback(self, answer: str, context: str) -> str:
        """格式化回答，如果没有检索到相关上下文则添加提示
        
        当RAG/知识图谱未返回有效结果时，在回答末尾添加免责声明，
        提醒用户回答仅基于模型通用知识。
        
        Args:
            answer: LLM生成的原始回答
            context: 检索到的上下文文本
            
        Returns:
            格式化后的回答字符串
        """
        # 定义无结果的关键词模式
        no_result_patterns = [
            "未找到相关医疗文献",
            "未找到相关知识库结果",
            "暂无相关信息",
            "没有找到匹配"
        ]
        
        # 检查上下文是否为空或包含无结果提示
        has_context = bool(context and context.strip())
        is_empty_result = (
            any(pattern in context for pattern in no_result_patterns) 
            if has_context else True
        )
        
        if not has_context or is_empty_result:
            fallback_hint = (
                "\n\n（未找到相关知识库结果，以上回答仅基于模型通用知识，仅供参考。）"
            )
            if fallback_hint not in answer:
                return answer.rstrip() + fallback_hint
        
        return answer
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        检查Agent及其依赖组件的状态。
        
        Returns:
            健康状态字典，包含status和details
        """
        status = "healthy"
        details = {
            "agent": self.name,
            "version": self.version,
            "tools_count": len(self.tools),
            "tools_status": {}
        }
        
        # 检查各工具状态
        for tool in self.tools:
            try:
                # 尝试调用工具的健康检查方法（如果有）
                if hasattr(tool, 'health_check'):
                    tool_health = tool.health_check()
                    details["tools_status"][tool.name] = tool_health
                    if tool_health.get("status") != "healthy":
                        status = "degraded"
                else:
                    details["tools_status"][tool.name] = {"status": "unknown"}
            except Exception as e:
                details["tools_status"][tool.name] = {
                    "status": "error",
                    "error": str(e)
                }
                status = "unhealthy"
        
        details["status"] = status
        return details


# 导出统计信息的便捷方法
def get_all_agents_stats() -> Dict[str, Dict]:
    """获取所有Agent的聚合统计信息
    
    Returns:
        以Agent名称为键的统计信息字典
    """
    return dict(BaseAgent._stats)

