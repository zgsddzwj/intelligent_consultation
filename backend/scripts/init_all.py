"""一键初始化所有数据"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.init_db import init_db
from scripts.init_knowledge_graph import init_knowledge_graph
from scripts.fetch_medical_data import save_medical_data_to_json, download_medical_documents
from app.utils.logger import app_logger


SERVICES = {
    "postgres": {"port": 5432, "name": "PostgreSQL"},
    "redis": {"port": 6379, "name": "Redis"},
    "neo4j": {"port": 7474, "name": "Neo4j"},
    "milvus": {"port": 19530, "name": "Milvus"},
}


def wait_for_services(timeout: int = 120):
    """等待依赖服务就绪（通过端口检测）"""
    import socket

    app_logger.info("[前置检查] 检测依赖服务是否就绪...")
    start_time = time.time()
    ready = set()

    while len(ready) < len(SERVICES) and time.time() - start_time < timeout:
        for service, config in SERVICES.items():
            if service in ready:
                continue
            try:
                with socket.create_connection(("localhost", config["port"]), timeout=1):
                    app_logger.info(f"  ✓ {config['name']} 已就绪")
                    ready.add(service)
            except (socket.timeout, ConnectionRefusedError, OSError):
                pass

        if len(ready) < len(SERVICES):
            time.sleep(2)

    if len(ready) < len(SERVICES):
        missing = [SERVICES[s]["name"] for s in SERVICES if s not in ready]
        app_logger.warning(f"  ⚠ 以下服务未就绪（将继续尝试）: {', '.join(missing)}")
    else:
        app_logger.info("  ✓ 所有依赖服务已就绪\n")


def init_all():
    """初始化所有数据"""
    try:
        app_logger.info("=" * 50)
        app_logger.info("开始初始化系统...")
        app_logger.info("=" * 50)

        # 前置：等待服务就绪
        wait_for_services(timeout=60)

        # 1. 初始化数据库表
        app_logger.info("[1/4] 初始化数据库表...")
        try:
            init_db()
            app_logger.info("  ✓ 数据库表初始化完成")
        except Exception as e:
            app_logger.error(f"  ✗ 数据库表初始化失败: {e}")
            app_logger.warning("  继续执行其他初始化步骤...")

        # 2. 获取医疗数据
        app_logger.info("[2/4] 获取医疗知识库数据...")
        try:
            save_medical_data_to_json()
            download_medical_documents()
            app_logger.info("  ✓ 医疗数据获取完成")
        except Exception as e:
            app_logger.error(f"  ✗ 医疗数据获取失败: {e}")

        # 3. 初始化Neo4j知识图谱
        app_logger.info("[3/4] 初始化Neo4j知识图谱...")
        try:
            init_knowledge_graph()
            app_logger.info("  ✓ 知识图谱初始化完成")
        except Exception as e:
            app_logger.error(f"  ✗ 知识图谱初始化失败: {e}")
            app_logger.warning("  请确保Neo4j服务已启动")

        # 4. 加载示例数据到向量数据库
        app_logger.info("[4/4] 加载示例数据到向量数据库...")
        try:
            from scripts.load_sample_data import load_sample_data_to_vector_db
            load_sample_data_to_vector_db()
            app_logger.info("  ✓ 向量数据库数据加载完成")
        except Exception as e:
            app_logger.error(f"  ✗ 向量数据库数据加载失败: {e}")
            app_logger.warning("  请确保Milvus服务已启动")

        app_logger.info("\n" + "=" * 50)
        app_logger.info("系统初始化完成！")
        app_logger.info("=" * 50)
        app_logger.info("\n下一步:")
        app_logger.info("  1. 启动服务: docker-compose up -d")
        app_logger.info("  2. 访问前端: http://localhost:3000")
        app_logger.info("  3. 访问API文档: http://localhost:8000/docs")

    except Exception as e:
        app_logger.error(f"初始化过程出错: {e}")
        raise


if __name__ == "__main__":
    init_all()
