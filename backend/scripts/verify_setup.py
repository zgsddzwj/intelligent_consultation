"""验证系统设置和配置"""
import sys
import os
import socket
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.utils.logger import app_logger


def check_env_file():
    """检查环境变量文件"""
    env_file = Path("./backend/.env")
    if not env_file.exists():
        app_logger.error("  ✗ .env文件不存在")
        return False

    app_logger.info("  ✓ .env文件存在")

    settings = get_settings()
    checks = [
        ("QWEN_API_KEY", settings.QWEN_API_KEY, "your_qwen_api_key_here"),
        ("DATABASE_URL", settings.DATABASE_URL, ""),
        ("REDIS_URL", settings.REDIS_URL, ""),
    ]

    all_ok = True
    for name, value, default in checks:
        if not value or value == default:
            app_logger.warning(f"  ⚠ {name} 未配置或使用默认值")
            all_ok = False
        else:
            app_logger.info(f"  ✓ {name} 已配置")

    return all_ok


def check_directories():
    """检查必要的目录"""
    required_dirs = [
        "./data/documents",
        "./data/knowledge_graph",
        "./data/sample",
        "./logs"
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            app_logger.info(f"  ✓ 创建目录: {dir_path}")
        else:
            app_logger.info(f"  ✓ 目录存在: {dir_path}")

    return True


def check_dependencies():
    """检查Python核心依赖"""
    required = {
        "fastapi": "FastAPI",
        "langchain": "LangChain",
        "neo4j": "Neo4j驱动",
        "dashscope": "DashScope",
        "pymilvus": "Milvus驱动",
        "redis": "Redis驱动",
        "sqlalchemy": "SQLAlchemy",
    }

    missing = []
    for module, name in required.items():
        try:
            __import__(module)
            app_logger.info(f"  ✓ {name} 已安装")
        except ImportError:
            app_logger.error(f"  ✗ {name} 未安装")
            missing.append(module)

    if missing:
        app_logger.info("  请运行: pip install -r requirements.txt")
        return False
    return True


def check_services():
    """检测本地依赖服务端口是否开放"""
    services = {
        "PostgreSQL": 5432,
        "Redis": 6379,
        "Neo4j HTTP": 7474,
        "Milvus": 19530,
    }

    all_ready = True
    for name, port in services.items():
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                app_logger.info(f"  ✓ {name} (端口 {port}) 已就绪")
        except (socket.timeout, ConnectionRefusedError, OSError):
            app_logger.warning(f"  ⚠ {name} (端口 {port}) 未就绪")
            all_ready = False

    return all_ready


def main():
    """运行所有检查"""
    app_logger.info("=" * 50)
    app_logger.info("系统设置验证")
    app_logger.info("=" * 50)

    results = []

    app_logger.info("\n[1/4] 检查环境变量...")
    results.append(("环境变量", check_env_file()))

    app_logger.info("\n[2/4] 检查目录结构...")
    results.append(("目录结构", check_directories()))

    app_logger.info("\n[3/4] 检查Python依赖...")
    results.append(("Python依赖", check_dependencies()))

    app_logger.info("\n[4/4] 检查本地服务...")
    results.append(("本地服务", check_services()))

    app_logger.info("\n" + "=" * 50)
    app_logger.info("验证结果")
    app_logger.info("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        app_logger.info(f"  {name}: {status}")

    if passed == total:
        app_logger.info("\n✓ 所有检查通过！可以开始初始化数据。")
        app_logger.info("\n下一步:")
        app_logger.info("  1. 启动服务: docker-compose up -d")
        app_logger.info("  2. 初始化数据: python scripts/init_all.py")
    else:
        app_logger.warning("\n⚠ 部分检查未通过，请先解决上述问题。")


if __name__ == "__main__":
    main()
