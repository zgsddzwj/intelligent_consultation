"""系统功能测试脚本"""
import sys
import requests
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logger import app_logger


def test_api_health(base_url: str = "http://localhost:8000"):
    """测试API健康检查"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            app_logger.info("✓ API健康检查通过")
            return True
        else:
            app_logger.error(f"✗ API健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"✗ API健康检查失败: {e}")
        return False


def test_consultation(base_url: str = "http://localhost:8000"):
    """测试咨询功能"""
    try:
        response = requests.post(
            f"{base_url}/api/v1/consultation/chat",
            json={
                "message": "我最近有点头痛，应该怎么办？",
                "user_id": 1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            app_logger.info("✓ 咨询功能测试通过")
            app_logger.info(f"  回答: {data.get('answer', '')[:100]}...")
            return True
        else:
            app_logger.error(f"✗ 咨询功能测试失败: {response.status_code}")
            app_logger.error(f"  错误: {response.text}")
            return False
    except Exception as e:
        app_logger.error(f"✗ 咨询功能测试失败: {e}")
        return False


def test_knowledge_graph(base_url: str = "http://localhost:8000"):
    """测试知识图谱API"""
    try:
        response = requests.get(
            f"{base_url}/api/v1/knowledge/graph/departments",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            dept_count = len(data.get("departments", []))
            app_logger.info(f"✓ 知识图谱API测试通过 (找到 {dept_count} 个科室)")
            return True
        else:
            app_logger.error(f"✗ 知识图谱API测试失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"✗ 知识图谱API测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    app_logger.info("=" * 50)
    app_logger.info("系统功能测试")
    app_logger.info("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # 等待服务启动
    app_logger.info("\n等待服务启动...")
    time.sleep(5)
    
    results = []
    
    # 测试API健康检查
    app_logger.info("\n[1/3] 测试API健康检查...")
    results.append(("API健康检查", test_api_health(base_url)))
    
    # 测试知识图谱
    app_logger.info("\n[2/3] 测试知识图谱API...")
    results.append(("知识图谱API", test_knowledge_graph(base_url)))
    
    # 测试咨询功能
    app_logger.info("\n[3/3] 测试咨询功能...")
    results.append(("咨询功能", test_consultation(base_url)))
    
    # 汇总结果
    app_logger.info("\n" + "=" * 50)
    app_logger.info("测试结果汇总")
    app_logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        app_logger.info(f"{name}: {status}")
    
    app_logger.info(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        app_logger.info("\n🎉 所有测试通过！系统运行正常。")
    else:
        app_logger.warning("\n⚠️  部分测试失败，请检查服务状态和配置。")


if __name__ == "__main__":
    main()

