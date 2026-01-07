"""检查导入状态"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.utils.logger import app_logger

try:
    client = get_neo4j_client()
    
    # 统计节点数
    result = client.execute_query('MATCH (n) RETURN count(n) as count')
    node_count = result[0]['count'] if result else 0
    
    # 统计关系数
    result2 = client.execute_query('MATCH ()-[r]->() RETURN count(r) as count')
    rel_count = result2[0]['count'] if result2 else 0
    
    # 按类型统计节点
    result3 = client.execute_query('''
        MATCH (n)
        RETURN labels(n)[0] as type, count(n) as count
        ORDER BY count DESC
    ''')
    
    print(f"\n{'='*50}")
    print(f"Neo4j知识图谱统计")
    print(f"{'='*50}")
    print(f"总节点数: {node_count:,}")
    print(f"总关系数: {rel_count:,}")
    print(f"\n节点类型分布:")
    for row in result3:
        print(f"  {row['type']}: {row['count']:,}")
    print(f"{'='*50}\n")
    
except Exception as e:
    print(f"❌ 连接Neo4j失败: {e}")
    print("\n请确保Neo4j服务已启动:")
    print("  - Docker: docker-compose up -d neo4j")
    print("  - 本地: 检查Neo4j服务状态")

