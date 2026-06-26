# 如何访问Neo4j数据库

## 方法1：Web浏览器访问（推荐）

1. **打开浏览器访问**：
   ```
   http://localhost:7474
   ```

2. **登录信息**：
   - 连接URL: `bolt://localhost:7687`
   - 用户名: `neo4j`
   - 密码: `medical123` (已修改，不能使用默认密码)

3. **使用Cypher查询**：
   在浏览器中输入Cypher查询语句，例如：
   ```cypher
   MATCH (n) RETURN count(n) as total_nodes
   MATCH ()-[r]->() RETURN count(r) as total_relationships
   MATCH (d:Disease) RETURN d.name LIMIT 10
   ```

## 方法2：使用Neo4j Desktop

1. 下载安装 Neo4j Desktop: https://neo4j.com/download/
2. 创建新项目
3. 连接到远程数据库：
   - Host: `localhost`
   - Port: `7687`
   - Username: `neo4j`
   - Password: `medical123`

## 方法3：使用命令行工具

```bash
# 进入Neo4j容器
docker exec -it medical_neo4j bash

# 使用cypher-shell
cypher-shell -u neo4j -p medical123
```

## 方法4：使用Python脚本查询

```python
from app.knowledge.graph.neo4j_client import get_neo4j_client

client = get_neo4j_client()

# 查询节点数
result = client.execute_query('MATCH (n) RETURN count(n) as count')
print(f"节点数: {result[0]['count']}")

# 查询关系数
result = client.execute_query('MATCH ()-[r]->() RETURN count(r) as count')
print(f"关系数: {result[0]['count']}")

# 查询疾病列表
result = client.execute_query('MATCH (d:Disease) RETURN d.name LIMIT 10')
for row in result:
    print(row['d.name'])
```

## 检查Neo4j状态

```bash
# 检查容器状态
docker ps | grep neo4j

# 查看日志
docker logs medical_neo4j --tail 50

# 检查端口
lsof -i :7474  # HTTP端口
lsof -i :7687  # Bolt端口
```

## 常用Cypher查询示例

```cypher
// 查看所有节点类型
MATCH (n)
RETURN labels(n)[0] as type, count(n) as count
ORDER BY count DESC

// 查看疾病及其症状
MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
WHERE d.name = '高血压'
RETURN d.name, collect(s.name) as symptoms

// 查看疾病及其治疗药物
MATCH (d:Disease)-[:TREATED_BY]->(dr:Drug)
WHERE d.name = '糖尿病'
RETURN d.name, collect(dr.name) as drugs

// 查看知识图谱可视化（限制节点数）
MATCH path = (d:Disease)-[*1..2]-(related)
WHERE d.name = '高血压'
RETURN path
LIMIT 50
```

