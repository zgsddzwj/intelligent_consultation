"""系统功能测试脚本"""
import sys
import requests
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logger import app_logger

BASE_URL = "http://localhost:8000"


def test_api_health():
    """测试API健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            app_logger.info(f"  ✓ API健康检查通过 (状态: {status})")
            return True
        else:
            app_logger.error(f"  ✗ API健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"  ✗ API健康检查失败: {e}")
        return False


def test_detailed_health():
    """测试详细健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            components = data.get("components", {})
            app_logger.info(f"  ✓ 详细健康检查通过")
            for name, info in components.items():
                icon = "✓" if info.get("status") == "healthy" else "⚠"
                app_logger.info(f"    {icon} {name}: {info.get('status')}")
            return True
        else:
            app_logger.error(f"  ✗ 详细健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"  ✗ 详细健康检查失败: {e}")
        return False


def test_knowledge_graph():
    """测试知识图谱API"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/knowledge/graph/departments",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            dept_count = len(data.get("departments", []))
            app_logger.info(f"  ✓ 知识图谱API测试通过 (找到 {dept_count} 个科室)")
            return True
        else:
            app_logger.error(f"  ✗ 知识图谱API测试失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"  ✗ 知识图谱API测试失败: {e}")
        return False


def test_consultation():
    """测试咨询功能"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/consultation/chat",
            json={
                "message": "我最近有点头痛，应该怎么办？",
                "user_id": 1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            answer = data.get("data", {}).get("answer", "")
            app_logger.info("  ✓ 咨询功能测试通过")
            app_logger.info(f"    回答摘要: {answer[:120]}...")
            return True
        else:
            app_logger.error(f"  ✗ 咨询功能测试失败: {response.status_code}")
            app_logger.error(f"    错误: {response.text[:200]}")
            return False
    except Exception as e:
        app_logger.error(f"  ✗ 咨询功能测试失败: {e}")
        return False


def test_agent_list():
    """测试Agent列表API"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/agents", timeout=10)
        if response.status_code == 200:
            data = response.json()
            agents = data.get("data", {}).get("agents", [])
            app_logger.info(f"  ✓ Agent列表测试通过 (找到 {len(agents)} 个Agent)")
            return True
        else:
            app_logger.error(f"  ✗ Agent列表测试失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"  ✗ Agent列表测试失败: {e}")
        return False


def test_metrics():
    """测试监控指标端点"""
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=10)
        if response.status_code == 200:
            app_logger.info("  ✓ 监控指标端点测试通过")
            return True
        else:
            app_logger.error(f"  ✗ 监控指标端点测试失败: {response.status_code}")
            return False
    except Exception as e:
        app_logger.error(f"  ✗ 监控指标端点测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    app_logger.info("=" * 50)
    app_logger.info("系统功能测试")
    app_logger.info("=" * 50)
    app_logger.info(f"目标地址: {BASE_URL}")

    # 等待服务启动
    app_logger.info("\n等待服务启动...")
    time.sleep(3)

    tests = [
        ("API健康检查", test_api_health),
        ("详细健康检查", test_detailed_health),
        ("知识图谱API", test_knowledge_graph),
        ("Agent列表", test_agent_list),
        ("监控指标", test_metrics),
        ("咨询功能", test_consultation),
    ]

    results = []
    for idx, (name, test_func) in enumerate(tests, 1):
        app_logger.info(f"\n[{idx}/{len(tests)}] 测试 {name}...")
        results.append((name, test_func()))

    # 汇总结果
    app_logger.info("\n" + "=" * 50)
    app_logger.info("测试结果汇总")
    app_logger.info("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        app_logger.info(f"  {status} {name}")

    app_logger.info(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        app_logger.info("\n🎉 所有测试通过！系统运行正常。")
    else:
        app_logger.warning("\n⚠ 部分测试失败，请检查服务状态和配置。")


if __name__ == "__main__":
    main()
