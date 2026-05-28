"""咨询API - 增强版（统一响应格式、增强校验、分页支持、OpenAPI优化）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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
from app.config import get_settings

settings = get_settings()
router = APIRouter()
orchestrator = AgentOrchestrator()


# ========== 请求/响应模型 ==========

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息内容")
    consultation_id: Optional[int] = Field(None, ge=1, description="咨询记录ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    user_id: Optional[int] = Field(None, ge=1, description="用户ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str = Field(..., description="AI回答内容")
    consultation_id: int = Field(..., description="咨询记录ID")
    sources: List[str] = Field(default=[], description="参考来源")
    risk_level: Optional[str] = Field(None, description="风险等级")
    execution_time: Optional[float] = Field(None, description="执行耗时(秒)")


class FeedbackRequest(BaseModel):
    """反馈请求"""
    consultation_id: int = Field(..., ge=1, description="咨询记录ID")
    trace_id: Optional[str] = Field(None, description="追踪ID")
    rating: int = Field(..., ge=1, le=5, description="评分1-5")
    comment: Optional[str] = Field(None, max_length=1000, description="评论内容")
    helpful: Optional[bool] = Field(None, description="是否有帮助")


class ConsultationHistoryResponse(BaseModel):
    """咨询历史响应"""
    id: int
    user_id: int
    agent_type: str
    status: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str


class PaginatedResponse(BaseModel):
    """分页响应基类"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========== 辅助函数 ==========

def _create_consultation_record(db: Session, user_id: Optional[int]) -> Consultation:
    """创建新的咨询记录"""
    consultation = Consultation(
        user_id=user_id or 1,
        agent_type=AgentType.DOCTOR,
        status=ConsultationStatus.IN_PROGRESS
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation


def _update_consultation_messages(
    consultation: Consultation,
    user_message: str,
    assistant_answer: str,
    sources: List[str],
    risk_level: Optional[str] = None
) -> None:
    """更新咨询记录的消息列表"""
    messages = consultation.messages or []
    messages.append({"role": "user", "content": user_message})
    messages.append({
        "role": "assistant",
        "content": assistant_answer,
        "sources": sources,
        "risk_level": risk_level
    })
    consultation.messages = messages
    consultation.status = ConsultationStatus.COMPLETED


# ========== 路由 ==========

@router.post("/chat", response_model=ChatResponse, summary="发送咨询消息", description="发送消息获取AI医疗咨询回答")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """发送咨询消息 - 增强版（含完整错误处理和数据库持久化）"""
    consultation_id = 0
    start_time = asyncio.get_event_loop().time()

    try:
        # 1. 验证输入
        is_valid, error_msg = validate_consultation_input({"message": request.message})
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # 2. 清理和脱敏用户输入
        sanitized_message = sanitize_user_input(request.message)

        # 3. 检测高风险内容
        risk_detection = detect_high_risk_content(sanitized_message)
        if risk_detection["requires_immediate_attention"]:
            return ChatResponse(
                answer=f"检测到高风险关键词，建议立即就医或拨打急救电话。\n\n{DISCLAIMER}",
                consultation_id=0,
                risk_level="high"
            )

        # 4. 创建或获取咨询记录
        consultation = None
        try:
            if request.consultation_id:
                consultation = db.query(Consultation).filter(
                    Consultation.id == request.consultation_id
                ).first()
                if consultation:
                    consultation_id = consultation.id

            if not consultation:
                consultation = _create_consultation_record(db, request.user_id)
                consultation_id = consultation.id
        except Exception as db_error:
            app_logger.warning(f"数据库操作失败，继续处理咨询: {db_error}")
            consultation = None

        # 5. 准备上下文
        context_data = request.context or {}
        if consultation and consultation.messages:
            context_data["history"] = consultation.messages[-10:]

        # 6. 使用编排器处理消息
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    orchestrator.process,
                    user_input=sanitized_message,
                    context=context_data
                ),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            app_logger.warning(f"咨询处理超时: consultation_id={consultation_id}")
            return ChatResponse(
                answer=f"请求处理超时，请重新发送您的问题。\n\n{DISCLAIMER}",
                consultation_id=consultation_id,
                sources=[],
                risk_level=None
            )

        # 7. 添加免责声明
        if result.get("answer"):
            result["answer"] += f"\n\n{DISCLAIMER}"

        # 8. 更新咨询记录
        if consultation:
            try:
                _update_consultation_messages(
                    consultation, request.message,
                    result.get("answer", ""),
                    result.get("sources", []),
                    result.get("risk_level")
                )
                db.commit()
            except Exception as db_error:
                app_logger.warning(f"更新咨询记录失败: {db_error}")

        execution_time = asyncio.get_event_loop().time() - start_time

        return ChatResponse(
            answer=result.get("answer", "抱歉，处理您的咨询时遇到问题，请稍后重试。"),
            consultation_id=consultation_id,
            sources=result.get("sources", []),
            risk_level=result.get("risk_level"),
            execution_time=round(execution_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"咨询处理失败: {e}", exc_info=True)
        error_msg = "抱歉，处理您的咨询时遇到技术问题。"
        if "rate limit" in str(e).lower():
            error_msg = "当前访问量较大，请稍后重试。"
        elif "timeout" in str(e).lower():
            error_msg = "请求处理超时，请重新发送您的问题。"
        elif "connection" in str(e).lower():
            error_msg = "服务暂时不可用，请稍后重试。"

        return ChatResponse(
            answer=f"{error_msg}请稍后重试或联系客服。",
            consultation_id=consultation_id,
            sources=[],
            risk_level=None
        )


@router.post("/chat/stream", response_model=None, summary="流式咨询接口", description="SSE流式返回AI回答")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """流式咨询接口（SSE）- 增强版"""
    consultation_id = 0

    # 验证输入
    is_valid, error_msg = validate_consultation_input({"message": request.message})
    if not is_valid:
        return StreamingResponse(
            iter([f"data: {json.dumps({'error': error_msg, 'type': 'error'})}\n\n"]),
            media_type="text/event-stream"
        )

    sanitized_message = sanitize_user_input(request.message)

    risk_detection = detect_high_risk_content(sanitized_message)
    if risk_detection["requires_immediate_attention"]:
        return StreamingResponse(
            iter([f"data: {json.dumps({'content': '检测到高风险关键词，建议立即就医或拨打急救电话。', 'type': 'message', 'done': True})}\n\n"]),
            media_type="text/event-stream"
        )

    async def generate_stream() -> AsyncGenerator[str, None]:
        nonlocal consultation_id

        try:
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
                    consultation = _create_consultation_record(db, request.user_id)
                    consultation_id = consultation.id
            except Exception as db_error:
                app_logger.warning(f"数据库操作失败: {db_error}")

            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'consultation_id': consultation_id})}\n\n"

            # 获取RAG上下文
            rag_context = ""
            sources = []
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        orchestrator.process,
                        user_input=sanitized_message,
                        context=request.context or {}
                    ),
                    timeout=30.0
                )
                rag_context = result.get("context_used", "")
                sources = result.get("sources", [])
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            except asyncio.TimeoutError:
                app_logger.warning("获取上下文超时，使用基础prompt")
            except Exception as e:
                app_logger.warning(f"获取上下文失败: {e}")

            # 构建prompt
            system_prompt = "你是一位专业的AI医疗助手。基于提供的医疗信息，为用户提供准确的医疗咨询。"
            if rag_context:
                prompt = f"基于以下医疗知识：\n{rag_context}\n\n用户问题：{sanitized_message}\n\n请提供专业、准确的回答。"
            else:
                prompt = f"用户问题：{sanitized_message}\n\n请提供专业、准确的回答。"

            full_answer = ""
            first_token_sent = False

            # 流式生成
            try:
                async for chunk in llm_service.stream_generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    user_id=str(request.user_id) if request.user_id else None,
                    session_id=str(consultation_id) if consultation_id else None
                ):
                    if chunk:
                        if not first_token_sent:
                            yield f"data: {json.dumps({'type': 'first_token'})}\n\n"
                            first_token_sent = True
                        full_answer += chunk
                        yield f"data: {json.dumps({'content': chunk, 'type': 'message'})}\n\n"
            except asyncio.TimeoutError:
                app_logger.warning("流式生成超时")
                yield f"data: {json.dumps({'type': 'error', 'error': '生成超时，请稍后重试'})}\n\n"

            # 添加免责声明
            disclaimer = f"\n\n{DISCLAIMER}"
            full_answer += disclaimer
            yield f"data: {json.dumps({'content': disclaimer, 'type': 'message'})}\n\n"

            # 更新咨询记录
            if consultation:
                try:
                    _update_consultation_messages(
                        consultation, request.message, full_answer, sources
                    )
                    db.commit()
                except Exception as db_error:
                    app_logger.warning(f"更新咨询记录失败: {db_error}")

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'consultation_id': consultation_id})}\n\n"

        except Exception as e:
            app_logger.error(f"流式咨询处理失败: {e}")
            yield f"data: {json.dumps({'error': '服务处理异常，请稍后重试', 'type': 'error'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/feedback", summary="提交用户反馈", description="对咨询结果进行评分和反馈")
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """提交用户反馈"""
    try:
        from app.services.langfuse_service import langfuse_service
        from app.services.feedback_analyzer import feedback_analyzer

        # 记录反馈到Langfuse
        if request.trace_id and langfuse_service.enabled:
            score_value = (request.rating - 1) / 4.0
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

        return {
            "success": True,
            "message": "反馈已提交",
            "analysis": feedback_analysis
        }

    except Exception as e:
        app_logger.error(f"提交反馈失败: {e}")
        raise HTTPException(status_code=500, detail="提交反馈失败，请稍后重试")


@router.get("/history", response_model=PaginatedResponse, summary="获取咨询历史", description="分页获取用户咨询历史记录")
async def get_consultation_history(
    user_id: Optional[int] = Query(None, ge=1, description="用户ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    consultation_repo: ConsultationRepository = Depends(get_consultation_repository)
):
    """获取咨询历史 - 增强版（支持分页）"""
    try:
        if user_id:
            consultations = consultation_repo.get_by_user_id(user_id, limit=page_size, offset=(page - 1) * page_size)
            total = consultation_repo.count_by_user_id(user_id)
        else:
            consultations = consultation_repo.get_all(limit=page_size, offset=(page - 1) * page_size, order_by="-created_at")
            total = consultation_repo.count_all()

        items = [
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

        total_pages = (total + page_size - 1) // page_size

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    except Exception as e:
        app_logger.error(f"获取咨询历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取咨询历史失败")


@router.get("/{consultation_id}", response_model=ConsultationHistoryResponse, summary="获取咨询详情", description="获取单条咨询记录的详细信息")
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
