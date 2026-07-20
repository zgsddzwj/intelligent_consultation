"""管理后台API — 用户管理/数据管理/安全设置/系统监控/导出报告"""
import time
import csv
import io
import json
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.dependencies import get_db, get_user_repository
from app.infrastructure.repositories.user_repository import UserRepository
from app.models.user import User, UserRole
from app.models.consultation import Consultation, ConsultationStatus, AgentType
from app.models.knowledge import KnowledgeDocument
from app.config import get_settings
from app.utils.logger import app_logger
from app.common.exceptions import NotFoundException, ValidationException, ErrorCode
from app.common.transaction import transactional

router = APIRouter()
settings = get_settings()

# 应用启动时间
_STARTUP_TIME = time.time()


# ========== 请求/响应模型 ==========

class UserListResponse(BaseModel):
    """用户列表响应"""
    users: List[dict]
    total: int
    page: int
    page_size: int


class UserUpdateRequest(BaseModel):
    """用户更新请求"""
    role: Optional[str] = Field(None, description="角色: patient/doctor/admin")
    is_active: Optional[bool] = Field(None, description="是否启用")
    full_name: Optional[str] = Field(None, description="姓名")


class UserBatchActionRequest(BaseModel):
    """用户批量操作请求"""
    user_ids: List[int] = Field(..., description="用户ID列表")
    action: str = Field(..., description="操作: activate/deactivate/delete")


class DataStatsResponse(BaseModel):
    """数据统计响应"""
    users: dict
    consultations: dict
    knowledge_documents: dict
    database: dict


class SecurityConfigResponse(BaseModel):
    """安全配置响应"""
    rbac: dict
    rate_limit: dict
    jwt: dict
    encryption: dict
    trusted_hosts: List[str]


class SystemMetricsResponse(BaseModel):
    """系统指标响应"""
    uptime_seconds: int
    version: str
    environment: str
    performance: dict
    alerts: dict
    components: dict


class ExportReportRequest(BaseModel):
    """导出报告请求"""
    format: str = Field("json", description="导出格式: json/csv")
    sections: List[str] = Field(
        default_factory=lambda: ["users", "consultations", "knowledge", "system"],
        description="导出内容模块"
    )


# ========== 用户管理 ==========

@router.get("/users", response_model=UserListResponse, summary="用户列表")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[str] = Query(None, description="按角色筛选"),
    keyword: Optional[str] = Query(None, description="搜索用户名/邮箱"),
    db: Session = Depends(get_db),
):
    """获取用户列表（支持分页、筛选、搜索）"""
    query = db.query(User)

    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass

    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            (User.username.ilike(like_pattern)) | (User.email.ilike(like_pattern))
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    user_list = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value if u.role else "patient",
            "full_name": u.full_name,
            "is_active": str(u.is_active) in ("1", "true", "True"),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]

    return UserListResponse(users=user_list, total=total, page=page, page_size=page_size)


@router.put("/users/{user_id}", summary="更新用户")
@transactional()
async def update_user(
    user_id: int,
    update: UserUpdateRequest,
    db: Session = Depends(get_db),
):
    """更新用户信息（角色/状态/姓名）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(f"用户 {user_id} 不存在", error_code=ErrorCode.DATA_NOT_FOUND)

    if update.role is not None:
        try:
            user.role = UserRole(update.role)
        except ValueError:
            raise ValidationException(f"无效的角色: {update.role}", error_code=ErrorCode.VALIDATION_ERROR)

    if update.is_active is not None:
        user.is_active = "1" if update.is_active else "0"

    if update.full_name is not None:
        user.full_name = update.full_name

    app_logger.info(f"管理员更新用户 {user_id}: role={update.role}, is_active={update.is_active}")
    return {"message": "用户更新成功", "user_id": user_id}


@router.delete("/users/{user_id}", summary="删除用户")
@transactional()
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(f"用户 {user_id} 不存在", error_code=ErrorCode.DATA_NOT_FOUND)

    db.delete(user)
    app_logger.info(f"管理员删除用户 {user_id}")
    return {"message": "用户删除成功", "user_id": user_id}


@router.post("/users/batch", summary="批量操作用户")
@transactional()
async def batch_action_users(
    request: UserBatchActionRequest,
    db: Session = Depends(get_db),
):
    """批量启用/禁用/删除用户"""
    affected = 0
    for uid in request.user_ids:
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            continue
        if request.action == "activate":
            user.is_active = "1"
            affected += 1
        elif request.action == "deactivate":
            user.is_active = "0"
            affected += 1
        elif request.action == "delete":
            db.delete(user)
            affected += 1

    app_logger.info(f"批量{request.action}用户: {affected} 条记录")
    return {"message": f"批量操作完成，影响 {affected} 条记录", "affected": affected}


# ========== 数据管理 ==========

@router.get("/data/stats", response_model=DataStatsResponse, summary="数据统计")
async def get_data_stats(db: Session = Depends(get_db)):
    """获取各数据表的统计信息"""
    # 用户统计
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == "1").count()
    doctor_count = db.query(User).filter(User.role == UserRole.DOCTOR).count()
    admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()

    # 咨询统计
    total_consultations = db.query(Consultation).count()
    completed_consultations = db.query(Consultation).filter(
        Consultation.status == ConsultationStatus.COMPLETED
    ).count()

    # 按Agent类型统计
    agent_stats = {}
    for agent_type in AgentType:
        count = db.query(Consultation).filter(Consultation.agent_type == agent_type).count()
        agent_stats[agent_type.value] = count

    # 知识文档统计
    total_docs = db.query(KnowledgeDocument).count()
    indexed_docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.is_indexed == "1").count()
    total_file_size = db.query(func.sum(KnowledgeDocument.file_size)).scalar() or 0

    # 数据库大小（PostgreSQL）
    db_size = 0
    try:
        result = db.execute(text("SELECT pg_database_size(current_database())")).scalar()
        db_size = result or 0
    except Exception:
        pass

    return DataStatsResponse(
        users={
            "total": total_users,
            "active": active_users,
            "doctors": doctor_count,
            "admins": admin_count,
        },
        consultations={
            "total": total_consultations,
            "completed": completed_consultations,
            "by_agent": agent_stats,
        },
        knowledge_documents={
            "total": total_docs,
            "indexed": indexed_docs,
            "unindexed": total_docs - indexed_docs,
            "total_file_size_bytes": total_file_size,
        },
        database={
            "size_bytes": db_size,
            "size_mb": round(db_size / 1024 / 1024, 2) if db_size else 0,
        },
    )


# ========== 安全设置 ==========

@router.get("/security/config", response_model=SecurityConfigResponse, summary="安全配置")
async def get_security_config():
    """获取当前安全配置（脱敏展示）"""
    from app.common.rbac import ROLE_PERMISSIONS, Permission

    role_permissions = {}
    for role, perms in ROLE_PERMISSIONS.items():
        role_permissions[role.value] = [p.value for p in perms]

    return SecurityConfigResponse(
        rbac={
            "enabled": settings.ENABLE_RBAC,
            "roles": role_permissions,
        },
        rate_limit={
            "enabled": settings.RATE_LIMIT_ENABLED,
            "max_calls": settings.RATE_LIMIT_CALLS,
            "period_seconds": settings.RATE_LIMIT_PERIOD,
            "fail_closed": settings.RATE_LIMIT_FAIL_CLOSED,
        },
        jwt={
            "algorithm": settings.ALGORITHM,
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
        },
        encryption={
            "enabled": settings.ENABLE_DATA_ENCRYPTION,
            "key_configured": bool(settings.ENCRYPTION_KEY),
        },
        trusted_hosts=settings.TRUSTED_HOSTS,
    )


# ========== 系统监控 ==========

@router.get("/system/metrics", response_model=SystemMetricsResponse, summary="系统指标")
async def get_system_metrics(db: Session = Depends(get_db)):
    """获取系统运行指标"""
    from app.infrastructure.monitoring import performance_monitor
    from app.services.redis_service import redis_service
    from app.knowledge.graph.neo4j_client import get_neo4j_client
    from app.services.milvus_service import get_milvus_service

    # 性能摘要
    perf_summary = performance_monitor.get_metrics_summary()

    # 告警状态
    alerts = performance_monitor.get_alerting_metrics()

    # 组件状态（轻量级检查）
    components = {}

    # PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        components["database"] = {"status": "healthy"}
    except Exception as e:
        components["database"] = {"status": "unhealthy", "error": str(e)[:100]}

    # Redis
    try:
        redis_info = redis_service.health_check()
        components["redis"] = {
            "status": redis_info.get("status", "unknown"),
            "connected_clients": redis_info.get("connected_clients"),
        }
    except Exception as e:
        components["redis"] = {"status": "unhealthy", "error": str(e)[:100]}

    # Neo4j
    try:
        neo4j = get_neo4j_client()
        neo4j_health = neo4j.health_check()
        components["neo4j"] = {
            "status": neo4j_health.get("status", "unknown"),
            "connected": neo4j_health.get("connected", False),
        }
    except Exception as e:
        components["neo4j"] = {"status": "unhealthy", "error": str(e)[:100]}

    # Milvus
    try:
        milvus = get_milvus_service()
        milvus_health = milvus.health_check()
        components["milvus"] = {
            "status": milvus_health.get("status", "unknown"),
        }
    except Exception as e:
        components["milvus"] = {"status": "unhealthy", "error": str(e)[:100]}

    # LLM
    if settings.LLM_PROVIDER == "deepseek" and settings.DEEPSEEK_API_KEY:
        components["llm"] = {"status": "healthy", "provider": "deepseek"}
    elif settings.LLM_PROVIDER == "qwen" and settings.QWEN_API_KEY:
        components["llm"] = {"status": "healthy", "provider": "qwen"}
    else:
        components["llm"] = {"status": "unhealthy", "error": "未配置"}

    return SystemMetricsResponse(
        uptime_seconds=int(time.time() - _STARTUP_TIME),
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        performance=perf_summary,
        alerts=alerts,
        components=components,
    )


# ========== 导出报告 ==========

@router.post("/export", summary="导出系统报告")
async def export_report(
    request: ExportReportRequest,
    db: Session = Depends(get_db),
):
    """导出系统报告（支持 JSON / CSV 格式）"""
    report_data: dict = {}
    report_data["exported_at"] = datetime.now().isoformat()
    report_data["version"] = settings.APP_VERSION

    if "users" in request.sections:
        users = db.query(User).order_by(User.created_at.desc()).all()
        report_data["users"] = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role.value if u.role else "patient",
                "is_active": str(u.is_active) in ("1", "true", "True"),
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ]

    if "consultations" in request.sections:
        consultations = db.query(Consultation).order_by(Consultation.created_at.desc()).all()
        report_data["consultations"] = [
            {
                "id": c.id,
                "user_id": c.user_id,
                "agent_type": c.agent_type.value if c.agent_type else "",
                "status": c.status.value if c.status else "",
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in consultations
        ]

    if "knowledge" in request.sections:
        docs = db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()
        report_data["knowledge_documents"] = [
            {
                "id": d.id,
                "title": d.title,
                "source": d.source,
                "file_type": d.file_type or "",
                "is_indexed": str(d.is_indexed) in ("1", "true", "True"),
                "file_size": d.file_size or 0,
                "created_at": d.created_at.isoformat() if d.created_at else "",
            }
            for d in docs
        ]

    if "system" in request.sections:
        report_data["system"] = {
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": int(time.time() - _STARTUP_TIME),
            "exported_at": datetime.now().isoformat(),
        }

    if request.format == "csv":
        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Section", "Field", "Value"])

        for section, data in report_data.items():
            if isinstance(data, list):
                for item in data:
                    for k, v in item.items():
                        writer.writerow([section, k, str(v)])
            elif isinstance(data, dict):
                for k, v in data.items():
                    writer.writerow([section, k, str(v)])

        output.seek(0)
        filename = f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    else:
        # JSON 格式
        filename = f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        content = json.dumps(report_data, ensure_ascii=False, indent=2)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
