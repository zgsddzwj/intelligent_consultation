"""日志配置"""
import sys
import json
from loguru import logger
from pathlib import Path
from app.config import get_settings

settings = get_settings()


def setup_logger():
    """配置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 结构化日志格式（JSON）
    def format_record(record):
        """格式化日志记录为JSON"""
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        
        # 添加请求ID（如果存在）- 延迟导入避免循环依赖
        try:
            from app.common.tracing import get_request_id
            request_id = get_request_id()
            if request_id:
                log_data["request_id"] = request_id
        except (ImportError, RuntimeError):
            pass
        
        # 添加异常信息
        if record["exception"]:
            log_data["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback
            }
        
        return json.dumps(log_data, ensure_ascii=False) + "\n"
    
    # 控制台输出（开发环境使用彩色格式）
    if settings.ENVIRONMENT == "development":
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.LOG_LEVEL,
            colorize=True
        )
    else:
        # 生产环境使用JSON格式
        logger.add(
            sys.stdout,
            format=format_record,
            level=settings.LOG_LEVEL,
            serialize=False
        )
    
    # 文件输出（使用简化的格式，避免格式错误）
    log_file = Path(settings.LOG_FILE)
    # 如果是相对路径，基于backend目录
    if not log_file.is_absolute():
        # 获取backend目录（app目录的父目录的父目录）
        backend_dir = Path(__file__).parent.parent.parent
        log_file = backend_dir / log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )
    
    return logger


# 初始化日志
app_logger = setup_logger()

