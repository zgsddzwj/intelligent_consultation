"""从QASystemOnMedicalKG项目导入医疗知识图谱数据 - 支持实时查看进度"""
import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, List, Any
from tqdm import tqdm
import time

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.knowledge.graph.builder import KnowledgeGraphBuilder
from app.utils.logger import app_logger


# QASystemOnMedicalKG数据URL
MEDICAL_JSON_URL = "https://raw.githubusercontent.com/liuhuanyong/QASystemOnMedicalKG/master/data/medical.json"
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "external"
MEDICAL_JSON_PATH = DATA_DIR / "medical.json"


def download_medical_data():
    """下载medical.json数据文件"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if MEDICAL_JSON_PATH.exists() and MEDICAL_JSON_PATH.stat().st_size > 0:
        app_logger.info(f"数据文件已存在: {MEDICAL_JSON_PATH} ({MEDICAL_JSON_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
        return
    
    app_logger.info(f"正在从 {MEDICAL_JSON_URL} 下载数据（约47MB，可能需要几分钟）...")
    try:
        # 使用流式下载
        response = requests.get(MEDICAL_JSON_URL, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(MEDICAL_JSON_PATH, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024) < 8192:  # 每MB打印一次
                            app_logger.info(f"下载进度: {downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB ({percent:.1f}%)")
        
        app_logger.info(f"数据下载完成: {MEDICAL_JSON_PATH} ({MEDICAL_JSON_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        app_logger.error(f"下载数据失败: {e}")
        if MEDICAL_JSON_PATH.exists():
            MEDICAL_JSON_PATH.unlink()  # 删除不完整的文件
        raise


def load_medical_data() -> List[Dict]:
    """加载medical.json数据（支持JSON数组或JSONL格式）"""
    if not MEDICAL_JSON_PATH.exists():
        download_medical_data()
    
    data = []
    with open(MEDICAL_JSON_PATH, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        
        # 尝试解析为JSON数组
        try:
            data = json.loads(content)
            if isinstance(data, list):
                app_logger.info(f"加载了 {len(data)} 条医疗数据（JSON数组格式）")
                return data
        except json.JSONDecodeError:
            pass
        
        # 尝试解析为JSONL格式（每行一个JSON对象）
        f.seek(0)
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                data.append(item)
            except json.JSONDecodeError as e:
                app_logger.warning(f"跳过第 {line_num} 行（JSON解析失败）: {e}")
        
        app_logger.info(f"加载了 {len(data)} 条医疗数据（JSONL格式）")
        return data


def extract_entities_and_relationships(data: List[Dict]) -> tuple:
    """提取实体和关系"""
    entities = {}  # {entity_type: {name: properties}}
    relationships = []  # [(from_type, from_name, rel_type, to_type, to_name, properties)]
    
    for item in tqdm(data, desc="解析数据"):
        disease_name = item.get("name", "")
        if not disease_name:
            continue
        
        # 创建疾病实体
        if "Disease" not in entities:
            entities["Disease"] = {}
        entities["Disease"][disease_name] = {
            "description": item.get("desc", ""),
            "prevent": item.get("prevent", ""),
            "cause": item.get("cause", ""),
            "easy_get": item.get("easy_get", ""),
            "cure_department": item.get("cure_department", ""),
            "cure_way": item.get("cure_way", ""),
            "cure_lasttime": item.get("cure_lasttime", ""),
            "cured_prob": item.get("cured_prob", ""),
        }
        
        # 处理症状
        for symptom in item.get("symptom", []):
            if "Symptom" not in entities:
                entities["Symptom"] = {}
            entities["Symptom"][symptom] = {}
            relationships.append(("Disease", disease_name, "HAS_SYMPTOM", "Symptom", symptom, {}))
        
        # 处理检查
        for check in item.get("check", []):
            if "Examination" not in entities:
                entities["Examination"] = {}
            entities["Examination"][check] = {}
            relationships.append(("Disease", disease_name, "REQUIRES_EXAM", "Examination", check, {}))
        
        # 处理药物
        for drug in item.get("drug", []):
            if "Drug" not in entities:
                entities["Drug"] = {}
            entities["Drug"][drug] = {}
            relationships.append(("Disease", disease_name, "TREATED_BY", "Drug", drug, {}))
        
        # 处理科室
        for dept in item.get("cure_department", []):
            if "Department" not in entities:
                entities["Department"] = {}
            entities["Department"][dept] = {}
            relationships.append(("Disease", disease_name, "BELONGS_TO", "Department", dept, {}))
        
        # 处理并发症
        for acompany in item.get("acompany", []):
            relationships.append(("Disease", disease_name, "ACCOMPANIES", "Disease", acompany, {}))
    
    return entities, relationships


def get_current_stats(builder: KnowledgeGraphBuilder) -> Dict:
    """获取当前Neo4j中的统计信息"""
    try:
        # 统计节点数
        result = builder.client.execute_query('MATCH (n) RETURN count(n) as count')
        node_count = result[0]['count'] if result else 0
        
        # 统计关系数
        result2 = builder.client.execute_query('MATCH ()-[r]->() RETURN count(r) as count')
        rel_count = result2[0]['count'] if result2 else 0
        
        # 按类型统计节点
        result3 = builder.client.execute_query('''
            MATCH (n)
            RETURN labels(n)[0] as type, count(n) as count
            ORDER BY count DESC
        ''')
        
        type_stats = {row['type']: row['count'] for row in result3}
        
        return {
            "nodes": node_count,
            "relationships": rel_count,
            "by_type": type_stats
        }
    except Exception as e:
        app_logger.warning(f"获取统计信息失败: {e}")
        return {"nodes": 0, "relationships": 0, "by_type": {}}


def import_to_neo4j(entities: Dict, relationships: List, batch_size: int = 100, show_progress: bool = True):
    """导入数据到Neo4j（支持实时查看进度）"""
    builder = KnowledgeGraphBuilder()
    builder.initialize_schema()
    
    app_logger.info("开始导入实体...")
    print("\n" + "="*60)
    print("📊 导入进度（可在Neo4j浏览器中实时查看: http://localhost:7474）")
    print("="*60)
    
    # 导入实体
    total_entities = sum(len(v) for v in entities.values())
    imported_entities = 0
    
    for entity_type, entity_dict in entities.items():
        if entity_type not in ["Disease", "Symptom", "Drug", "Examination", "Department"]:
            continue  # 跳过未定义的实体类型
        
        for name, properties in tqdm(entity_dict.items(), desc=f"导入{entity_type}", leave=False):
            try:
                # 清理空值
                clean_props = {k: v for k, v in properties.items() if v}
                builder.create_entity(entity_type, name, clean_props, merge=True)
                imported_entities += 1
                
                # 每导入一定数量后显示统计（减少频率）
                if show_progress and imported_entities % 500 == 0:
                    stats = get_current_stats(builder)
                    print(f"✅ 已导入 {imported_entities}/{total_entities} 个实体 | Neo4j: {stats['nodes']} 节点, {stats['relationships']} 关系")
            except Exception as e:
                # 只在debug模式下记录详细错误
                if imported_entities % 100 == 0:  # 每100个错误才记录一次
                    app_logger.debug(f"创建实体失败 {entity_type}:{name}: {e}")
    
    app_logger.info("开始导入关系...")
    print(f"\n✅ 实体导入完成！共导入 {imported_entities} 个实体")
    
    # 导入关系
    imported_rels = 0
    for from_type, from_name, rel_type, to_type, to_name, props in tqdm(relationships, desc="导入关系"):
        try:
            # 只导入已定义的关系类型
            if rel_type in ["HAS_SYMPTOM", "REQUIRES_EXAM", "TREATED_BY", "BELONGS_TO"]:
                builder.create_relationship(from_type, from_name, rel_type, to_type, to_name, props)
                imported_rels += 1
                
                # 每导入一定数量后显示统计（减少频率）
                if show_progress and imported_rels % 5000 == 0:
                    stats = get_current_stats(builder)
                    print(f"✅ 已导入 {imported_rels}/{len(relationships)} 条关系 | Neo4j: {stats['nodes']} 节点, {stats['relationships']} 关系")
        except Exception as e:
            # 只在debug模式下记录详细错误
            if imported_rels % 1000 == 0:  # 每1000个错误才记录一次
                app_logger.debug(f"创建关系失败: {from_type}({from_name})-[{rel_type}]->{to_type}({to_name}): {e}")
    
    # 最终统计
    final_stats = get_current_stats(builder)
    print("\n" + "="*60)
    print("🎉 导入完成！")
    print("="*60)
    print(f"✅ 导入统计:")
    print(f"   - 实体: {imported_entities} 个")
    print(f"   - 关系: {imported_rels} 条")
    print(f"\n📊 Neo4j最终统计:")
    print(f"   - 总节点数: {final_stats['nodes']:,}")
    print(f"   - 总关系数: {final_stats['relationships']:,}")
    print(f"\n📈 节点类型分布:")
    for entity_type, count in sorted(final_stats['by_type'].items(), key=lambda x: x[1], reverse=True):
        print(f"   - {entity_type}: {count:,}")
    print(f"\n🔍 在Neo4j浏览器中查看: http://localhost:7474")
    print("="*60 + "\n")


def main():
    """主函数"""
    app_logger.info("开始导入QASystemOnMedicalKG医疗知识图谱数据...")
    print("\n" + "="*60)
    print("🚀 开始导入医疗知识图谱数据")
    print("="*60)
    print("💡 提示: 可以在导入过程中打开 http://localhost:7474 实时查看数据")
    print("="*60 + "\n")
    
    # 加载数据
    data = load_medical_data()
    
    # 提取实体和关系
    entities, relationships = extract_entities_and_relationships(data)
    
    app_logger.info(f"提取到 {sum(len(v) for v in entities.values())} 个实体")
    app_logger.info(f"提取到 {len(relationships)} 条关系")
    
    print(f"\n📦 数据准备完成:")
    print(f"   - 实体: {sum(len(v) for v in entities.values()):,} 个")
    print(f"   - 关系: {len(relationships):,} 条")
    print(f"\n开始导入到Neo4j...\n")
    
    # 导入到Neo4j
    import_to_neo4j(entities, relationships, show_progress=True)
    
    app_logger.info("数据导入完成！")


if __name__ == "__main__":
    main()

