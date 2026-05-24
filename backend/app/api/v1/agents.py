"""Agent管理API - 增强版（统一响应格式、标准化错误处理、健康检查聚合）"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.agents.doctor_agent import DoctorAgent
from app.agents.health_manager_agent import HealthManagerAgent
from app.agents.customer_service_agent import CustomerServiceAgent
from app.agents.operations_agent import OperationsAgent
from app.common.exceptions import NotFoundException, ExternalServiceException, ErrorCode
from app.utils.logger import app_logger
from app.agents.base import get_all_agents_stats

router = APIRouter()

# Agent实例（单例）
agents = {
    "doctor": DoctorAgent(),
    "health_manager": HealthManagerAgent(),
    "customer_service": CustomerServiceAgent(),
    "operations": OperationsAgent()
}


# ========== 响应模型 ==========

class AgentInfo(BaseModel):
    """Agent信息"""
    id: str
    name: str
    description: str
    version: str
    tools: List[str]
    tool_count: int


class AgentStatus(BaseModel):
    """Agent状态"""
    agent_id: str
    name: str
    status: str
    version: str
    tools_count: int
    health: Dict[str, Any]


class InvokeAgentRequest(BaseModel):
    """调用Agent请求"""
    input_data: Dict[str, Any] = Field(..., description="输入数据")
    timeout: Optional[float] = Field(30.0, ge=1.0, le=120.0, description="超时时间（秒）")


class InvokeAgentResponse(BaseModel):
    """调用Agent响应"""
    success: bool = True
    data: Dict[str, Any]
    agent_id: str
    execution_time: float


class ApiResponse(BaseModel):
    """统一API响应格式"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None


# ========== 辅助函数 ==========

def _get_agent_or_raise(agent_id: str):
    """获取Agent，不存在则抛出异常"""
    if agent_id not in agents:
        raise NotFoundException(
            message=f"Agent '{agent_id}' 不存在",
            error_code=ErrorCode.DATA_NOT_FOUND,
            details={"available_agents": list(agents.keys())}
        )
    return agents[agent_id]


# ========== 路由 ==========

@router.get("", response_model=ApiResponse)
async def get_agents():
    """获取所有Agent列表"""
    agent_list = [
        AgentInfo(
            id=agent_id,
            name=agent.name,
            description=agent.description,
            version=agent.version,
            tools=[tool.name for tool in agent.tools],
            tool_count=len(agent.tools)
        )
        for agent_id, agent in agents.items()
    ]
    
    return {
        "success": True,
        "data": agent_list,
        "message": f"共 {len(agent_list)} 个Agent"
    }


@router.post("/{agent_id}/invoke", response_model=ApiResponse)
async def invoke_agent(agent_id: str, request: InvokeAgentRequest):
    """调用特定Agent处理请求"""
    agent = _get_agent_or_raise(agent_id)
    
    try:
        import asyncio
        # 使用超时控制
        result = await asyncio.wait_for(
            asyncio.to_thread(agent.process, request.input_data),
            timeout=request.timeout
        )
        
        return {
            "success": True,
            "data": {
                "agent_id": agent_id,
                "result": result,
                "execution_time": result.get("execution_time", 0.0)
            },
            "message": "Agent执行成功"
        }
        
    except asyncio.TimeoutError:
        app_logger.error(f"Agent执行超时: {agent_id}")
        raise ExternalServiceException(
            message=f"Agent '{agent_id}' 执行超时（{request.timeout}秒）",
            error_code=ErrorCode.AGENT_ERROR,
            details={"agent_id": agent_id, "timeout": request.timeout}
        )
    except Exception as e:
        app_logger.error(f"调用Agent失败: {agent_id}, {e}")
        raise ExternalServiceException(
            message=f"Agent '{agent_id}' 执行失败: {str(e)}",
            error_code=ErrorCode.AGENT_ERROR,
            details={"agent_id": agent_id, "error_type": type(e).__name__}
        )


@router.get("/{agent_id}/status", response_model=ApiResponse)
async def get_agent_status(agent_id: str):
    """获取Agent详细状态（含健康检查）"""
    agent = _get_agent_or_raise(agent_id)
    
    # 执行健康检查
    health = agent.health_check()
    
    return {
        "success": True,
        "data": AgentStatus(
            agent_id=agent_id,
            name=agent.name,
            status=health.get("status", "unknown"),
            version=agent.version,
            tools_count=len(agent.tools),
            health=health
        ),
        "message": f"Agent '{agent_id}' 状态: {health.get('status', 'unknown')}"
    }


@router.get("/{agent_id}/stats", response_model=ApiResponse)
async def get_agent_stats(agent_id: str):
    """获取Agent执行统计"""
    agent = _get_agent_or_raise(agent_id)
    
    stats = agent.get_stats()
    class_stats = get_all_agents_stats().get(agent_id, {})
    
    return {
        "success": True,
        "data": {
            **stats,
            "class_level_stats": class_stats
        },
        "message": f"Agent '{agent_id}' 统计信息"
    }


@router.post("/{agent_id}/health", response_model=ApiResponse)
async def check_agent_health(agent_id: str):
    """执行Agent健康检查"""
    agent = _get_agent_or_raise(agent_id)
    
    health = agent.health_check()
    status = health.get("status", "unknown")
    
    http_status = status.HTTP_200_OK
    if status == "unhealthy":
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif status == "degraded":
        http_status = status.HTTP_200_OK
    
    return {
        "success": status != "unhealthy",
        "data": health,
        "message": f"Agent '{agent_id}' 健康状态: {status}"
    }
