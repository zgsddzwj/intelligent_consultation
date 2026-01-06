"""Agent管理API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.agents.doctor_agent import DoctorAgent
from app.agents.health_manager_agent import HealthManagerAgent
from app.agents.customer_service_agent import CustomerServiceAgent
from app.agents.operations_agent import OperationsAgent
from app.utils.logger import app_logger

router = APIRouter()

# Agent实例
agents = {
    "doctor": DoctorAgent(),
    "health_manager": HealthManagerAgent(),
    "customer_service": CustomerServiceAgent(),
    "operations": OperationsAgent()
}


class AgentInfo(BaseModel):
    """Agent信息"""
    id: str
    name: str
    description: str
    tools: List[str]


class InvokeAgentRequest(BaseModel):
    """调用Agent请求"""
    input_data: Dict[str, Any]


class InvokeAgentResponse(BaseModel):
    """调用Agent响应"""
    agent_id: str
    result: Dict[str, Any]
    execution_time: float


@router.get("", response_model=List[AgentInfo])
async def get_agents():
    """获取所有Agent"""
    return [
        AgentInfo(
            id=agent_id,
            name=agent.name,
            description=agent.description,
            tools=[tool.name for tool in agent.tools]
        )
        for agent_id, agent in agents.items()
    ]


@router.post("/{agent_id}/invoke", response_model=InvokeAgentResponse)
async def invoke_agent(agent_id: str, request: InvokeAgentRequest):
    """调用特定Agent"""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
    
    try:
        agent = agents[agent_id]
        result = agent.process(request.input_data)
        
        return InvokeAgentResponse(
            agent_id=agent_id,
            result=result,
            execution_time=result.get("execution_time", 0.0)
        )
    except Exception as e:
        app_logger.error(f"调用Agent失败: {agent_id}, {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """获取Agent状态"""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} 不存在")
    
    agent = agents[agent_id]
    return {
        "agent_id": agent_id,
        "name": agent.name,
        "status": "active",
        "tools_count": len(agent.tools)
    }

