"""咨询API"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
import json
import asyncio
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_consultation_repository
from app.infrastructure.repositories.consultation_repository import ConsultationRepository
from app.agents.orchestrator import AgentOrchestrator
from app.models.consultation import Consultation, ConsultationStatus, AgentType
from app.utils.logger import app_logger
from app.utils.validators import validate_consultation_input, detect_high_risk_content, sanitize_user_input
from app.utils.security import DISCLAIMER
from app.services.llm_service import llm_service

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
    consultation_id = 0
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
        
        # 尝试创建或获取咨询记录（如果数据库可用）
        try:
            if request.consultation_id:
                consultation = db.query(Consultation).filter(
                    Consultation.id == request.consultation_id
                ).first()
                if not consultation:
                    raise HTTPException(status_code=404, detail="咨询记录不存在")
                consultation_id = consultation.id
            else:
                consultation = Consultation(
                    user_id=request.user_id or 1,  # 默认用户ID
                    agent_type=AgentType.DOCTOR,  # 默认医生Agent
                    status=ConsultationStatus.IN_PROGRESS
                )
                db.add(consultation)
                db.commit()
                db.refresh(consultation)
                consultation_id = consultation.id
        except Exception as db_error:
            app_logger.warning(f"数据库操作失败，继续处理咨询: {db_error}")
            consultation = None
        
        # 准备上下文（包含历史记录）
        context_data = request.context or {}
        if consultation and consultation.messages:
            # 获取最近10条历史记录作为上下文
            context_data["history"] = consultation.messages[-10:]
            
        # 使用编排器处理消息
        result = orchestrator.process(
            user_input=sanitized_message,
            context=context_data
        )
        
        # 添加免责声明
        if result.get("answer"):
            result["answer"] += f"\n\n{DISCLAIMER}"
        
        # 尝试更新咨询记录（如果数据库可用）
        if consultation:
            try:
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
            except Exception as db_error:
                app_logger.warning(f"更新咨询记录失败: {db_error}")
        
        return ChatResponse(
            answer=result.get("answer", "抱歉，处理您的咨询时遇到问题，请稍后重试。"),
            consultation_id=consultation_id,
            sources=result.get("sources", []),
            risk_level=result.get("risk_level"),
            execution_time=result.get("execution_time")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"咨询处理失败: {e}")
        # 即使出错也返回基本响应
        return ChatResponse(
            answer=f"处理您的咨询时遇到错误: {str(e)}。请稍后重试或联系客服。",
            consultation_id=consultation_id,
            sources=[],
            risk_level=None
        )


@router.post("/chat/stream", response_model=None)
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """流式咨询接口（SSE）"""
    consultation_id = 0
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        nonlocal consultation_id
        
        try:
            # 验证输入
            is_valid, error_msg = validate_consultation_input({"message": request.message})
            if not is_valid:
                yield f"data: {json.dumps({'error': error_msg, 'type': 'error'})}\n\n"
                return
            
            # 清理和脱敏用户输入
            sanitized_message = sanitize_user_input(request.message)
            
            # 检测高风险内容
            risk_detection = detect_high_risk_content(sanitized_message)
            if risk_detection["requires_immediate_attention"]:
                yield f"data: {json.dumps({'content': '检测到高风险关键词，建议立即就医或拨打急救电话。', 'type': 'message', 'done': True})}\n\n"
                return
            
            # 创建或获取咨询记录
            consultation = None
            try:
                if request.consultation_id:
                    consultation = db.query(Consultation).filter(
                        Consultation.id == request.consultation_id
                    ).first()
                    if consultation:
                        consultation_id = consultation.id
                else:
                    consultation = Consultation(
                        user_id=request.user_id or 1,
                        agent_type=AgentType.DOCTOR,
                        status=ConsultationStatus.IN_PROGRESS
                    )
                    db.add(consultation)
                    db.commit()
                    db.refresh(consultation)
                    consultation_id = consultation.id
            except Exception as db_error:
                app_logger.warning(f"数据库操作失败: {db_error}")
            
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'consultation_id': consultation_id})}\n\n"
            
            # 使用编排器获取上下文（同步执行，快速完成）
            # 这样可以获得RAG检索和知识图谱查询的结果
            rag_context = ""
            sources = []
            try:
                result = orchestrator.process(
                    user_input=sanitized_message,
                    context=request.context or {}
                )
                
                # 获取检索到的上下文
                rag_context = result.get("context_used", "")
                sources = result.get("sources", [])
                
                # 发送检索完成信号和来源信息
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            except Exception as e:
                app_logger.warning(f"获取上下文失败，使用基础prompt: {e}")
            
            # 构建包含上下文的prompt
            system_prompt = "你是一位专业的AI医疗助手。基于提供的医疗信息，为用户提供准确的医疗咨询。"
            
            if rag_context:
                prompt = f"基于以下医疗知识：\n{rag_context}\n\n用户问题：{sanitized_message}\n\n请提供专业、准确的回答。"
            else:
                prompt = f"用户问题：{sanitized_message}\n\n请提供专业、准确的回答。"
            
            full_answer = ""
            first_token_sent = False
            
            # 流式生成
            async for chunk in llm_service.stream_generate(
                prompt=prompt,
                system_prompt=system_prompt,
                user_id=str(request.user_id) if request.user_id else None,
                session_id=str(consultation_id) if consultation_id else None
            ):
                if chunk:
                    if not first_token_sent:
                        # 记录首token时间
                        yield f"data: {json.dumps({'type': 'first_token'})}\n\n"
                        first_token_sent = True
                    
                    full_answer += chunk
                    yield f"data: {json.dumps({'content': chunk, 'type': 'message'})}\n\n"
            
            # 添加免责声明
            disclaimer = f"\n\n{DISCLAIMER}"
            full_answer += disclaimer
            yield f"data: {json.dumps({'content': disclaimer, 'type': 'message'})}\n\n"
            
            # 更新咨询记录
            if consultation:
                try:
                    messages = consultation.messages or []
                    messages.append({
                        "role": "user",
                        "content": request.message
                    })
                    messages.append({
                        "role": "assistant",
                        "content": full_answer,
                        "sources": sources,
                        "risk_level": None
                    })
                    consultation.messages = messages
                    consultation.status = ConsultationStatus.COMPLETED
                    db.commit()
                except Exception as db_error:
                    app_logger.warning(f"更新咨询记录失败: {db_error}")
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'consultation_id': consultation_id})}\n\n"
            
        except Exception as e:
            app_logger.error(f"流式咨询处理失败: {e}")
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
        )


class FeedbackRequest(BaseModel):
    """反馈请求"""
    consultation_id: int
    trace_id: Optional[str] = None
    rating: int  # 1-5分
    comment: Optional[str] = None
    helpful: Optional[bool] = None  # 是否有帮助


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """提交用户反馈"""
    try:
        from app.services.langfuse_service import langfuse_service
        from app.services.feedback_analyzer import feedback_analyzer
        
        # 记录反馈到Langfuse
        if request.trace_id and langfuse_service.enabled:
            # 将rating转换为0-1范围
            score_value = (request.rating - 1) / 4.0  # 1->0, 5->1
            langfuse_service.score(
                trace_id=request.trace_id,
                name="user_rating",
                value=score_value,
                comment=request.comment
            )
        
        # 分析反馈
        feedback_analysis = feedback_analyzer.analyze(
            rating=request.rating,
            comment=request.comment,
            helpful=request.helpful
        )
        
        # 可以存储到数据库
        # feedback_record = Feedback(...)
        # db.add(feedback_record)
        # db.commit()
        
        return {
            "success": True,
            "message": "反馈已提交",
            "analysis": feedback_analysis
        }
        
    except Exception as e:
        app_logger.error(f"提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[ConsultationHistoryResponse])
async def get_consultation_history(
    user_id: Optional[int] = None,
    limit: int = 10,
    consultation_repo: ConsultationRepository = Depends(get_consultation_repository)
):
    """获取咨询历史"""
    try:
        if user_id:
            consultations = consultation_repo.get_by_user_id(user_id, limit=limit)
        else:
            consultations = consultation_repo.get_all(limit=limit, order_by="-created_at")
        
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
async def get_consultation(
    consultation_id: int,
    consultation_repo: ConsultationRepository = Depends(get_consultation_repository)
):
    """获取咨询详情"""
    consultation = consultation_repo.get_by_id_or_raise(consultation_id)
    
    return ConsultationHistoryResponse(
        id=consultation.id,
        user_id=consultation.user_id,
        agent_type=consultation.agent_type.value,
        status=consultation.status.value,
        messages=consultation.messages or [],
        created_at=consultation.created_at.isoformat() if consultation.created_at else "",
        updated_at=consultation.updated_at.isoformat() if consultation.updated_at else ""
    )

