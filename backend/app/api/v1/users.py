"""用户管理API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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

router = APIRouter()


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str
    email: str
    password: str
    role: Optional[str] = "patient"


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
    
    # 创建用户
    hashed_password = get_password_hash(user.password)
    role = UserRole(user.role) if user.role in [r.value for r in UserRole] else UserRole.PATIENT
    
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
    user_repo: UserRepository = Depends(get_user_repository)
):
    """用户登录，返回 JWT 访问令牌"""
    user = user_repo.get_by_username(credentials.username)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise UnauthorizedException("用户名或密码错误")

    if str(user.is_active) not in ("1", "true", "True"):
        raise UnauthorizedException("用户已被禁用")

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
    })

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

