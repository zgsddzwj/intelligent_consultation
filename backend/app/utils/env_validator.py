"""环境变量配置验证模块

在应用启动时验证必要的环境变量是否配置正确
"""
import os
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger


class EnvValidator:
    """环境变量验证器"""
    
    # 必需的环境变量
    REQUIRED_VARS = [
        "DATABASE_URL",
        "REDIS_URL",
    ]
    
    # 条件必需的环境变量（根据功能启用情况）
    CONDITIONAL_VARS = {
        "QWEN_API_KEY": "使用通义千问LLM服务",
        "DEEPSEEK_API_KEY": "使用DeepSeek LLM服务",
        "NEO4J_URI": "使用Neo4j知识图谱",
        "MILVUS_HOST": "使用Milvus向量数据库",
    }
    
    # 可选的环境变量（有默认值）
    OPTIONAL_VARS = [
        "LOG_LEVEL",
        "MAX_WORKERS",
        "CONTEXT_MAX_TOKENS",
        "RATE_LIMIT_RPS",
    ]
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """验证环境变量配置
        
        Returns:
            验证结果报告
        """
        report = {
            "valid": True,
            "missing_required": [],
            "missing_conditional": [],
            "warnings": [],
            "configured": []
        }
        
        # 检查必需变量
        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            if not value:
                report["missing_required"].append(var)
                report["valid"] = False
            else:
                # 隐藏敏感信息
                display_value = cls._mask_sensitive_value(var, value)
                report["configured"].append(f"{var}={display_value}")
        
        # 检查条件必需变量
        for var, description in cls.CONDITIONAL_VARS.items():
            if not os.getenv(var):
                report["missing_conditional"].append({
                    "variable": var,
                    "description": description
                })
        
        # 检查可选变量
        for var in cls.OPTIONAL_VARS:
            value = os.getenv(var)
            if value:
                report["configured"].append(f"{var}={value}")
            else:
                report["warnings"].append(f"{var} 未设置，将使用默认值")
        
        # 记录验证结果
        if report["valid"]:
            app_logger.info("环境变量验证通过")
            if report["missing_conditional"]:
                app_logger.warning(
                    f"部分功能缺少配置: {', '.join([x['variable'] for x in report['missing_conditional']])}"
                )
        else:
            app_logger.error(
                f"环境变量验证失败，缺少必需变量: {', '.join(report['missing_required'])}"
            )
        
        return report
    
    @classmethod
    def _mask_sensitive_value(cls, var_name: str, value: str) -> str:
        """对敏感值进行掩码处理"""
        sensitive_keywords = ["KEY", "SECRET", "PASSWORD", "TOKEN", "URI"]
        if any(keyword in var_name.upper() for keyword in sensitive_keywords):
            if len(value) > 8:
                return value[:4] + "****" + value[-4:]
            return "****"
        return value


def validate_env() -> bool:
    """便捷函数：验证环境变量
    
    Returns:
        验证是否通过
    """
    report = EnvValidator.validate()
    return report["valid"]
