"""咨询API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.agents.orchestrator import AgentOrchestrator
from app.models.consultation import Consultation, ConsultationStatus, AgentType
from app.utils.logger import app_logger
from app.utils.validators import validate_consultation_input, detect_high_risk_content, sanitize_user_input
from app.utils.security import DISCLAIMER

router = APIRouter()
orchestrator = AgentOrchestrator()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    consultation_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str
    consultation_id: int
    sources: List[str] = []
    risk_level: Optional[str] = None
    execution_time: Optional[float] = None


class ConsultationHistoryResponse(BaseModel):
    """咨询历史响应"""
    id: int
    user_id: int
    agent_type: str
    status: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """发送咨询消息"""
    try:
        # 验证输入
        is_valid, error_msg = validate_consultation_input({"message": request.message})
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 清理和脱敏用户输入
        sanitized_message = sanitize_user_input(request.message)
        
        # 检测高风险内容
        risk_detection = detect_high_risk_content(sanitized_message)
        if risk_detection["requires_immediate_attention"]:
            return ChatResponse(
                answer=f"检测到高风险关键词，建议立即就医或拨打急救电话。\n\n{DISCLAIMER}",
                consultation_id=0,
                risk_level="high"
            )
        
        # 创建或获取咨询记录
        if request.consultation_id:
            consultation = db.query(Consultation).filter(
                Consultation.id == request.consultation_id
            ).first()
            if not consultation:
                raise HTTPException(status_code=404, detail="咨询记录不存在")
        else:
            consultation = Consultation(
                user_id=request.user_id or 1,  # 默认用户ID
                agent_type=AgentType.DOCTOR,  # 默认医生Agent
                status=ConsultationStatus.IN_PROGRESS
            )
            db.add(consultation)
            db.commit()
            db.refresh(consultation)
        
        # 使用编排器处理消息
        result = orchestrator.process(
            user_input=sanitized_message,
            context=request.context or {}
        )
        
        # 添加免责声明
        if result.get("answer"):
            result["answer"] += f"\n\n{DISCLAIMER}"
        
        # 更新咨询记录
        messages = consultation.messages or []
        messages.append({
            "role": "user",
            "content": request.message
        })
        messages.append({
            "role": "assistant",
            "content": result.get("answer", ""),
            "sources": result.get("sources", []),
            "risk_level": result.get("risk_level")
        })
        
        consultation.messages = messages
        consultation.status = ConsultationStatus.COMPLETED
        db.commit()
        
        return ChatResponse(
            answer=result.get("answer", ""),
            consultation_id=consultation.id,
            sources=result.get("sources", []),
            risk_level=result.get("risk_level"),
            execution_time=result.get("execution_time")
        )
        
    except Exception as e:
        app_logger.error(f"咨询处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[ConsultationHistoryResponse])
async def get_consultation_history(
    user_id: Optional[int] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取咨询历史"""
    try:
        query = db.query(Consultation)
        if user_id:
            query = query.filter(Consultation.user_id == user_id)
        
        consultations = query.order_by(
            Consultation.created_at.desc()
        ).limit(limit).all()
        
        return [
            ConsultationHistoryResponse(
                id=c.id,
                user_id=c.user_id,
                agent_type=c.agent_type.value,
                status=c.status.value,
                messages=c.messages or [],
                created_at=c.created_at.isoformat() if c.created_at else "",
                updated_at=c.updated_at.isoformat() if c.updated_at else ""
            )
            for c in consultations
        ]
    except Exception as e:
        app_logger.error(f"获取咨询历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{consultation_id}", response_model=ConsultationHistoryResponse)
async def get_consultation(consultation_id: int, db: Session = Depends(get_db)):
    """获取咨询详情"""
    consultation = db.query(Consultation).filter(
        Consultation.id == consultation_id
    ).first()
    
    if not consultation:
        raise HTTPException(status_code=404, detail="咨询记录不存在")
    
    return ConsultationHistoryResponse(
        id=consultation.id,
        user_id=consultation.user_id,
        agent_type=consultation.agent_type.value,
        status=consultation.status.value,
        messages=consultation.messages or [],
        created_at=consultation.created_at.isoformat() if consultation.created_at else "",
        updated_at=consultation.updated_at.isoformat() if consultation.updated_at else ""
    )

