"""用户管理API"""
import asyncio
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_user_repository
from app.infrastructure.repositories.user_repository import UserRepository
from app.models.user import User, UserRole
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.common.exceptions import UnauthorizedException
from app.utils.logger import app_logger
from app.common.exceptions import NotFoundException, ValidationException, ErrorCode
from app.common.transaction import transactional
from app.services.redis_service import redis_service

router = APIRouter()

# ========== 登录安全限制 ==========
MAX_LOGIN_ATTEMPTS = 5  # 最大失败次数
LOGIN_LOCKOUT_SECONDS = 300  # 锁定时长（5分钟）
LOGIN_ATTEMPT_WINDOW = 300  # 失败计数窗口（5分钟）


def _get_client_ip(request: Request) -> str:
    """取直连客户端IP（不用X-Forwarded-For：该头可被伪造，锁定键会被绕过）"""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _get_login_attempt_key(username: str, ip: str) -> str:
    # 按用户名+来源IP组合计数：防止攻击者对已知用户名跨IP连错实现定向锁号(DoS)
    return f"login_attempts:{username}:{ip}"


def _get_login_lockout_key(username: str, ip: str) -> str:
    return f"login_lockout:{username}:{ip}"


async def _check_login_lockout(username: str, ip: str) -> None:
    """检查该来源对账号是否已被锁定，锁定时抛出异常"""
    if not redis_service.enabled:
        return  # Redis 不可用时降级跳过

    lockout = await asyncio.to_thread(redis_service.get, _get_login_lockout_key(username, ip))
    if lockout:
        remaining = await asyncio.to_thread(redis_service.ttl, _get_login_lockout_key(username, ip))
        raise UnauthorizedException(
            f"登录失败次数过多，已被暂时锁定，请在 {remaining} 秒后重试"
        )


async def _record_login_failure(username: str, ip: str) -> None:
    """记录登录失败，达阈值时锁定该来源对该账号的尝试"""
    if not redis_service.enabled:
        return

    key = _get_login_attempt_key(username, ip)
    attempts = await asyncio.to_thread(redis_service.incr, key)
    if attempts == 1:
        # 第一次失败时设置窗口过期时间
        await asyncio.to_thread(redis_service.expire, key, LOGIN_ATTEMPT_WINDOW)

    if attempts and attempts >= MAX_LOGIN_ATTEMPTS:
        # 达到上限 → 锁定
        await asyncio.to_thread(
            redis_service.set,
            _get_login_lockout_key(username, ip),
            "1",
            ttl=LOGIN_LOCKOUT_SECONDS
        )
        app_logger.warning(
            f"来源 {ip} 对账号 {username} 连续登录失败被锁定 {LOGIN_LOCKOUT_SECONDS}s"
        )


async def _clear_login_failures(username: str, ip: str) -> None:
    """登录成功后清除失败记录"""
    if not redis_service.enabled:
        return

    await asyncio.to_thread(redis_service.delete, _get_login_attempt_key(username, ip))
    await asyncio.to_thread(redis_service.delete, _get_login_lockout_key(username, ip))


class UserCreate(BaseModel):
    """创建用户请求（角色固定为患者，角色变更仅允许管理员端点操作）

    校验规则与前端注册表单保持一致（用户名≥3位、密码≥6位、邮箱格式）。
    """
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录令牌响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str
    role: str
    full_name: Optional[str] = None


@router.post("/register", response_model=UserResponse)
@transactional()
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """注册用户"""
    # 检查用户名是否已存在
    existing_user = user_repo.get_by_username(user.username)
    if existing_user:
        raise ValidationException("用户名已存在", error_code=ErrorCode.VALIDATION_ERROR)
    
    # 检查邮箱是否已存在
    existing_email = user_repo.get_by_email(user.email)
    if existing_email:
        raise ValidationException("邮箱已存在", error_code=ErrorCode.VALIDATION_ERROR)
    
    # 创建用户（公开注册一律为患者角色，防止自选 admin 提权）
    # bcrypt 为纯 CPU 密集操作，移入线程池避免阻塞事件循环
    hashed_password = await asyncio.to_thread(get_password_hash, user.password)
    role = UserRole.PATIENT
    
    new_user = user_repo.create(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role
    )
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=new_user.role.value,
        full_name=new_user.full_name
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """用户登录，返回 JWT 访问令牌（含登录失败次数限制）"""
    client_ip = _get_client_ip(request)

    # 1. 检查账号是否被锁定
    await _check_login_lockout(credentials.username, client_ip)

    # 2. 验证用户（密码校验为 CPU 密集操作，移入线程池避免阻塞事件循环）
    user = user_repo.get_by_username(credentials.username)
    if not user or not await asyncio.to_thread(verify_password, credentials.password, user.hashed_password):
        # 记录失败
        await _record_login_failure(credentials.username, client_ip)
        raise UnauthorizedException("用户名或密码错误")

    if str(user.is_active) not in ("1", "true", "True"):
        raise UnauthorizedException("用户已被禁用")

    # 3. 登录成功 → 清除失败记录
    await _clear_login_failures(credentials.username, client_ip)

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
    })

    app_logger.info(f"用户登录成功: {user.username} (id={user.id})")

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """获取用户信息"""
    user = user_repo.get_by_id_or_raise(user_id)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        full_name=user.full_name
    )
