"""数据加密工具"""
from cryptography.fernet import Fernet
from typing import Optional
import base64
import os
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class DataEncryption:
    """数据加密类"""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        初始化加密器
        
        Args:
            key: 加密密钥，如果为None则从配置或环境变量获取
        """
        if key is None:
            # 从配置获取密钥，如果没有则生成新的
            encryption_key = getattr(settings, "ENCRYPTION_KEY", None)
            if encryption_key:
                if isinstance(encryption_key, str):
                    key = encryption_key.encode()
                else:
                    key = encryption_key
            else:
                # 生成新密钥（仅用于开发环境）
                key = Fernet.generate_key()
                app_logger.warning("使用自动生成的加密密钥，生产环境请设置ENCRYPTION_KEY")
        
        self.cipher = Fernet(key)
        self.key = key
    
    def encrypt(self, data: str) -> str:
        """加密数据"""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            app_logger.error(f"加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            app_logger.error(f"解密失败: {e}")
            raise
    
    def encrypt_dict(self, data: dict, fields: list) -> dict:
        """加密字典中的指定字段"""
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result
    
    def decrypt_dict(self, data: dict, fields: list) -> dict:
        """解密字典中的指定字段"""
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(str(result[field]))
                except Exception:
                    # 如果解密失败，保持原值（可能已经是明文）
                    pass
        return result


# 全局加密器实例
_encryption_instance: Optional[DataEncryption] = None


def get_encryption() -> DataEncryption:
    """获取加密器实例（单例）"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption()
    return _encryption_instance


def encrypt_sensitive_field(value: str) -> str:
    """加密敏感字段"""
    return get_encryption().encrypt(value)


def decrypt_sensitive_field(encrypted_value: str) -> str:
    """解密敏感字段"""
    return get_encryption().decrypt(encrypted_value)

