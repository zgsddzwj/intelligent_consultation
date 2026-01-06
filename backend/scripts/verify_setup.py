"""验证系统设置和配置"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.utils.logger import app_logger


def check_env_file():
    """检查环境变量文件"""
    env_file = Path("./backend/.env")
    if not env_file.exists():
        app_logger.error("✗ .env文件不存在")
        return False
    
    app_logger.info("✓ .env文件存在")
    
    # 检查关键配置
    settings = get_settings()
    
    if not settings.QWEN_API_KEY or settings.QWEN_API_KEY == "your_qwen_api_key_here":
        app_logger.warning("⚠️  QWEN_API_KEY未配置或使用默认值")
        return False
    
    app_logger.info("✓ QWEN_API_KEY已配置")
    return True


def check_directories():
    """检查必要的目录"""
    required_dirs = [
        "./data/documents",
        "./data/knowledge_graph",
        "./data/sample",
        "./logs"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            app_logger.info(f"✓ 创建目录: {dir_path}")
        else:
            app_logger.info(f"✓ 目录存在: {dir_path}")
    
    return all_exist


def check_dependencies():
    """检查Python依赖"""
    try:
        import fastapi
        import langchain
        import neo4j
        import dashscope
        app_logger.info("✓ 核心依赖已安装")
        return True
    except ImportError as e:
        app_logger.error(f"✗ 缺少依赖: {e}")
        app_logger.info("请运行: pip install -r requirements.txt")
        return False


def main():
    """运行所有检查"""
    app_logger.info("=" * 50)
    app_logger.info("系统设置验证")
    app_logger.info("=" * 50)
    
    results = []
    
    app_logger.info("\n[1/3] 检查环境变量...")
    results.append(("环境变量", check_env_file()))
    
    app_logger.info("\n[2/3] 检查目录结构...")
    results.append(("目录结构", check_directories()))
    
    app_logger.info("\n[3/3] 检查Python依赖...")
    results.append(("Python依赖", check_dependencies()))
    
    app_logger.info("\n" + "=" * 50)
    app_logger.info("验证结果")
    app_logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        app_logger.info(f"{name}: {status}")
    
    if passed == total:
        app_logger.info("\n✓ 所有检查通过！可以开始初始化数据。")
        app_logger.info("\n下一步:")
        app_logger.info("1. 启动服务: docker-compose up -d")
        app_logger.info("2. 初始化数据: python scripts/init_all.py")
    else:
        app_logger.warning("\n⚠️  部分检查未通过，请先解决上述问题。")


if __name__ == "__main__":
    main()

