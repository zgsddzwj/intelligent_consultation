"""Agent基类模块 - 增强版（执行超时控制、工具调用重试、健康检查增强）

提供所有Agent的抽象基类，定义统一的接口和通用功能：
- 工具管理（注册、执行、追踪）
- LLM调用封装（带重试和缓存）
- 执行日志记录
- Langfuse可观测性集成
- 回答格式化和降级处理
- 执行超时控制
- 工具调用重试机制
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import time
import functools
from app.services.llm_service import llm_service
from app.services.langfuse_service import langfuse_service
from app.utils.logger import app_logger


# 默认超时配置
DEFAULT_AGENT_TIMEOUT = 30.0  # Agent整体执行超时
DEFAULT_TOOL_TIMEOUT = 10.0   # 单个工具调用超时
DEFAULT_TOOL_RETRIES = 2      # 工具调用重试次数


def with_timeout(timeout_seconds: float):
    """
    执行超时装饰器
    
    使用线程池实现同步函数的超时控制。
    
    Args:
        timeout_seconds: 超时时间（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 使用线程池执行带超时的调用
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FutureTimeoutError:
                    app_logger.error(
                        f"Agent执行超时: {func.__name__} 超过 {timeout_seconds}秒"
                    )
                    raise TimeoutError(
                        f"Agent执行超时，已超过 {timeout_seconds}秒限制"
                    )
        return wrapper
    return decorator


class BaseAgent(ABC):
    """Agent抽象基类（增强版）
    
    所有专业Agent（医生、健康管家、客服、运营）的基类，
    提供统一的工具管理、LLM调用和可观测性能力。
    
    新增功能：
    - 执行超时控制
    - 工具调用重试
    - 增强健康检查
    - 执行统计聚合
    
    Attributes:
        name: Agent名称标识
        description: Agent功能描述
        llm: LLM服务实例
        tools: 已注册的工具列表
        version: Agent版本号
        stats: 执行统计信息
        timeout: 执行超时时间
    """
    
    # 类级别的统计信息
    _stats: Dict[str, Dict] = {}
    
    def __init__(self, name: str, description: str, version: str = "1.0.0",
                 timeout: float = DEFAULT_AGENT_TIMEOUT):
        """
        初始化Agent实例
        
        Args:
            name: Agent唯一名称标识
            description: Agent的功能描述
            version: Agent版本号，默认1.0.0
            timeout: 执行超时时间（秒）
        """
        self.name = name
        self.description = description
        self.version = version
        self.timeout = timeout
        self.llm = llm_service
        self.tools: List[Any] = []
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "timeout_calls": 0,
            "total_execution_time": 0.0,
            "tools_usage": {},
            "tool_failures": {}
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
        """获取Agent的系统Prompt"""
        pass
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户输入并返回结果"""
        pass
    
    def add_tool(self, tool: Any) -> None:
        """注册工具到Agent"""
        if not hasattr(tool, 'name'):
            raise ValueError(f"工具缺少name属性: {type(tool)}")
        if not hasattr(tool, 'execute') or not callable(getattr(tool, 'execute')):
            raise ValueError(f"工具缺少execute方法: {tool.name}")
        
        existing_names = [t.name for t in self.tools]
        if tool.name in existing_names:
            app_logger.warning(f"Agent {self.name}: 工具 {tool.name} 已存在，将被替换")
            self.tools = [t for t in self.tools if t.name != tool.name]
        
        self.tools.append(tool)
        app_logger.debug(f"Agent {self.name} 注册工具: {tool.name}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """移除已注册的工具"""
        original_len = len(self.tools)
        self.tools = [t for t in self.tools if t.name != tool_name]
        removed = len(self.tools) < original_len
        if removed:
            app_logger.debug(f"Agent {self.name} 移除工具: {tool_name}")
        return removed
    
    def get_tool(self, tool_name: str) -> Any:
        """获取指定工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有已注册的工具"""
        return [
            {"name": t.name, "description": getattr(t, 'description', '')}
            for t in self.tools
        ]
    
    def execute_tool(self, tool_name: str, trace_id: Optional[str] = None,
                     parent_observation_id: Optional[str] = None,
                     max_retries: int = DEFAULT_TOOL_RETRIES,
                     timeout: float = DEFAULT_TOOL_TIMEOUT,
                     **kwargs) -> Any:
        """
        执行指定工具（带重试和超时）
        
        改进点：
        - 支持配置重试次数
        - 支持配置超时时间
        - 失败时记录详细错误信息
        - 自动降级策略
        
        Args:
            tool_name: 要执行的工具名称
            trace_id: Langfuse追踪ID
            parent_observation_id: 父级观察ID
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            **kwargs: 传递给工具的参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 工具不存在
            TimeoutError: 执行超时
            Exception: 工具执行失败（超过重试次数）
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
                    "parameters": {k: str(v)[:100] for k, v in kwargs.items()},
                    "max_retries": max_retries,
                    "timeout": timeout
                }
            )
            parent_observation_id = span.id if span and hasattr(span, 'id') else parent_observation_id
        
        start_time = time.time()
        last_error = None
        
        # 查找工具
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break
        
        if not tool:
            error_msg = f"工具 '{tool_name}' 在Agent '{self.name}' 中不存在。可用工具: {[t.name for t in self.tools]}"
            if span:
                try:
                    span.end(metadata={"success": False, "error": error_msg})
                except:
                    pass
            raise ValueError(error_msg)
        
        # 带重试的执行
        for attempt in range(max_retries + 1):
            try:
                # 使用线程池实现超时控制
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(tool.execute, **kwargs)
                    result = future.result(timeout=timeout)
                
                # 更新工具使用统计
                tool_key = f"{self.name}.{tool_name}"
                self.stats["tools_usage"][tool_key] = \
                    self.stats["tools_usage"].get(tool_key, 0) + 1
                
                # 记录成功
                execution_time = time.time() - start_time
                if langfuse_service.enabled and span:
                    try:
                        span.end(metadata={
                            "success": True,
                            "execution_time": execution_time,
                            "result_size": len(str(result)),
                            "attempts": attempt + 1
                        })
                    except Exception:
                        pass
                
                app_logger.debug(
                    f"工具执行成功: {tool_name} (尝试 {attempt + 1}/{max_retries + 1}, "
                    f"耗时 {execution_time:.3f}s)"
                )
                
                return result
                
            except FutureTimeoutError:
                last_error = TimeoutError(f"工具 {tool_name} 执行超时 ({timeout}s)")
                app_logger.warning(
                    f"工具执行超时 (尝试 {attempt + 1}/{max_retries + 1}): {tool_name}"
                )
            except Exception as e:
                last_error = e
                app_logger.warning(
                    f"工具执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {tool_name} - {e}"
                )
                
                # 更新失败统计
                failure_key = f"{tool_name}:{type(e).__name__}"
                self.stats["tool_failures"][failure_key] = \
                    self.stats["tool_failures"].get(failure_key, 0) + 1
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                retry_delay = 0.5 * (attempt + 1)  # 递增延迟
                time.sleep(retry_delay)
        
        # 所有重试都失败了
        execution_time = time.time() - start_time
        if langfuse_service.enabled and span:
            try:
                span.end(metadata={
                    "success": False,
                    "error": str(last_error)[:500],
                    "execution_time": execution_time,
                    "attempts": max_retries + 1
                })
            except Exception:
                pass
        
        app_logger.error(
            f"工具执行最终失败: {tool_name} (已尝试 {max_retries + 1} 次)"
        )
        raise last_error
    
    def log_execution(self, input_data: Dict, output_data: Dict, 
                     execution_time: float, tools_used: List[str] = None) -> Dict:
        """记录执行日志并更新统计信息"""
        # 更新统计
        self.stats["total_calls"] += 1
        self.stats["total_execution_time"] += execution_time
        
        if output_data.get("error"):
            self.stats["failed_calls"] += 1
        else:
            self.stats["successful_calls"] += 1
        
        # 更新类级别统计
        BaseAgent._stats[self.name]["instance_calls"] += 1
        BaseAgent._stats[self.name]["last_called"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
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
        
        # 慢执行告警
        if execution_time > self.timeout * 0.8:
            app_logger.warning(
                f"[{self.name}] 执行接近超时: {execution_time:.3f}s / {self.timeout}s"
            )
        
        app_logger.info(
            f"[{self.name}] 执行完成: {log_data['execution_time']}s, 工具: {log_data['tools_used']}"
        )
        return log_data
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Agent执行统计信息"""
        total = self.stats["total_calls"]
        avg_time = (self.stats["total_execution_time"] / total) if total > 0 else 0
        success_rate = (self.stats["successful_calls"] / total * 100) if total > 0 else 0
        
        return {
            "agent": self.name,
            "version": self.version,
            "timeout": self.timeout,
            "total_calls": total,
            "successful_calls": self.stats["successful_calls"],
            "failed_calls": self.stats["failed_calls"],
            "timeout_calls": self.stats["timeout_calls"],
            "success_rate": round(success_rate, 2),
            "avg_execution_time": round(avg_time, 3),
            "total_execution_time": round(self.stats["total_execution_time"], 3),
            "tools_registered": len(self.tools),
            "tools_usage": dict(self.stats["tools_usage"]),
            "tool_failures": dict(self.stats["tool_failures"])
        }
    
    def format_answer_with_fallback(self, answer: str, context: str) -> str:
        """格式化回答，如果没有检索到相关上下文则添加提示"""
        no_result_patterns = [
            "未找到相关医疗文献",
            "未找到相关知识库结果",
            "暂无相关信息",
            "没有找到匹配"
        ]
        
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
        """增强健康检查"""
        status = "healthy"
        details = {
            "agent": self.name,
            "version": self.version,
            "timeout": self.timeout,
            "tools_count": len(self.tools),
            "tools_status": {},
            "stats_summary": {
                "total_calls": self.stats["total_calls"],
                "success_rate": (
                    f"{self.stats['successful_calls'] / max(self.stats['total_calls'], 1) * 100:.1f}%"
                )
            }
        }
        
        # 检查各工具状态
        unhealthy_tools = 0
        for tool in self.tools:
            try:
                if hasattr(tool, 'health_check'):
                    tool_health = tool.health_check()
                    details["tools_status"][tool.name] = tool_health
                    if tool_health.get("status") != "healthy":
                        unhealthy_tools += 1
                        status = "degraded"
                else:
                    details["tools_status"][tool.name] = {"status": "unknown"}
            except Exception as e:
                unhealthy_tools += 1
                details["tools_status"][tool.name] = {
                    "status": "error",
                    "error": str(e)[:200]
                }
                status = "unhealthy"
        
        # 如果失败率过高，标记为degraded
        if self.stats["total_calls"] > 10:
            failure_rate = self.stats["failed_calls"] / self.stats["total_calls"]
            if failure_rate > 0.3:  # 失败率超过30%
                status = "degraded"
                details["degraded_reason"] = f"高失败率: {failure_rate * 100:.1f}%"
        
        details["status"] = status
        details["unhealthy_tools"] = unhealthy_tools
        return details


# 导出统计信息的便捷方法
def get_all_agents_stats() -> Dict[str, Dict]:
    """获取所有Agent的聚合统计信息"""
    return dict(BaseAgent._stats)
