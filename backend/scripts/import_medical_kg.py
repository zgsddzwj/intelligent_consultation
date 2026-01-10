"""从QASystemOnMedicalKG项目导入医疗知识图谱数据"""
import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, List, Any
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.graph.builder import KnowledgeGraphBuilder
from app.utils.logger import app_logger


# QASystemOnMedicalKG数据URL
MEDICAL_JSON_URL = "https://raw.githubusercontent.com/liuhuanyong/QASystemOnMedicalKG/master/data/medical.json"
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "external"
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


def map_entity_type(kg_type: str) -> str:
    """映射QASystemOnMedicalKG的实体类型到当前项目的实体类型"""
    type_mapping = {
        "disease": "Disease",
        "symptom": "Symptom",
        "drug": "Drug",
        "check": "Examination",
        "department": "Department",
        "food": "Food",  # 可能需要扩展schema
        "producer": "Producer",  # 可能需要扩展schema
    }
    return type_mapping.get(kg_type.lower(), "Disease")


def map_relationship_type(rel: str) -> str:
    """映射关系类型"""
    rel_mapping = {
        "has_symptom": "HAS_SYMPTOM",
        "acompany_with": "ACCOMPANIES",  # 可能需要扩展schema
        "belongs_to": "BELONGS_TO",
        "common_drug": "TREATED_BY",
        "do_eat": "RECOMMENDED_FOOD",  # 可能需要扩展schema
        "drugs_of": "TREATED_BY",
        "need_check": "REQUIRES_EXAM",
        "no_eat": "CONTRAINDICATED_FOOD",  # 可能需要扩展schema
        "recommand_drug": "TREATED_BY",
        "recommand_eat": "RECOMMENDED_FOOD",
    }
    return rel_mapping.get(rel.lower(), "RELATED_TO")


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


def import_to_neo4j(entities: Dict, relationships: List, batch_size: int = 100):
    """导入数据到Neo4j"""
    builder = KnowledgeGraphBuilder()
    builder.initialize_schema()
    
    app_logger.info("开始导入实体...")
    
    # 导入实体
    for entity_type, entity_dict in entities.items():
        if entity_type not in ["Disease", "Symptom", "Drug", "Examination", "Department"]:
            continue  # 跳过未定义的实体类型
        
        for name, properties in tqdm(entity_dict.items(), desc=f"导入{entity_type}"):
            try:
                # 清理空值
                clean_props = {k: v for k, v in properties.items() if v}
                builder.create_entity(entity_type, name, clean_props, merge=True)
            except Exception as e:
                app_logger.warning(f"创建实体失败 {entity_type}:{name}: {e}")
    
    app_logger.info("开始导入关系...")
    
    # 导入关系
    for from_type, from_name, rel_type, to_type, to_name, props in tqdm(relationships, desc="导入关系"):
        try:
            # 只导入已定义的关系类型
            if rel_type in ["HAS_SYMPTOM", "REQUIRES_EXAM", "TREATED_BY", "BELONGS_TO"]:
                builder.create_relationship(from_type, from_name, rel_type, to_type, to_name, props)
        except Exception as e:
            app_logger.warning(f"创建关系失败: {from_type}({from_name})-[{rel_type}]->{to_type}({to_name}): {e}")


def main():
    """主函数"""
    app_logger.info("开始导入QASystemOnMedicalKG医疗知识图谱数据...")
    
    # 加载数据
    data = load_medical_data()
    
    # 提取实体和关系
    entities, relationships = extract_entities_and_relationships(data)
    
    app_logger.info(f"提取到 {sum(len(v) for v in entities.values())} 个实体")
    app_logger.info(f"提取到 {len(relationships)} 条关系")
    
    # 导入到Neo4j
    import_to_neo4j(entities, relationships)
    
    app_logger.info("数据导入完成！")


if __name__ == "__main__":
    main()

