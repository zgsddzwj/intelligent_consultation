"""RBAC（基于角色的访问控制）"""
from enum import Enum
from typing import List, Optional, Set
from functools import wraps
from fastapi import HTTPException, status, Depends
from app.models.user import UserRole
from app.utils.logger import app_logger


class Permission(str, Enum):
    """权限枚举"""
    # 用户权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # 咨询权限
    CONSULTATION_READ = "consultation:read"
    CONSULTATION_WRITE = "consultation:write"
    CONSULTATION_DELETE = "consultation:delete"
    
    # 知识库权限
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_DELETE = "knowledge:delete"
    
    # 管理权限
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"


# 角色权限映射
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.PATIENT: {
        Permission.USER_READ,
        Permission.CONSULTATION_READ,
        Permission.CONSULTATION_WRITE,
        Permission.KNOWLEDGE_READ,
    },
    UserRole.DOCTOR: {
        Permission.USER_READ,
        Permission.CONSULTATION_READ,
        Permission.CONSULTATION_WRITE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_WRITE,
    },
    UserRole.ADMIN: {
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.CONSULTATION_READ,
        Permission.CONSULTATION_WRITE,
        Permission.CONSULTATION_DELETE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_WRITE,
        Permission.KNOWLEDGE_DELETE,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
        Permission.ADMIN_DELETE,
    },
}


def get_user_permissions(role: UserRole) -> Set[Permission]:
    """获取角色的权限"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: UserRole, permission: Permission) -> bool:
    """检查角色是否有权限"""
    permissions = get_user_permissions(role)
    return permission in permissions


def require_permission(permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中获取用户角色（需要实现认证中间件）
            # 这里先返回函数，实际使用时需要从JWT token中获取用户信息
            user_role = kwargs.get("user_role") or UserRole.PATIENT
            
            if not has_permission(user_role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要权限: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*allowed_roles: UserRole):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = kwargs.get("user_role") or UserRole.PATIENT
            
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要角色: {[r.value for r in allowed_roles]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RBACService:
    """RBAC服务"""
    
    @staticmethod
    def check_permission(role: UserRole, permission: Permission) -> bool:
        """检查权限"""
        return has_permission(role, permission)
    
    @staticmethod
    def get_permissions(role: UserRole) -> Set[Permission]:
        """获取角色权限"""
        return get_user_permissions(role)
    
    @staticmethod
    def can_access_resource(role: UserRole, resource_type: str, action: str) -> bool:
        """检查是否可以访问资源"""
        permission_str = f"{resource_type}:{action}"
        try:
            permission = Permission(permission_str)
            return has_permission(role, permission)
        except ValueError:
            app_logger.warning(f"未知权限: {permission_str}")
            return False

