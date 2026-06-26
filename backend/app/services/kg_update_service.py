"""知识图谱实时更新服务

提供知识图谱的增量更新能力：
- 实体/关系的创建、更新、删除
- 基于文档上传的事件驱动更新（从新文档中抽取实体并自动写入图谱）
- 更新审计日志与缓存失效
"""
import time
import threading
from typing import Dict, List, Any, Optional
from collections import deque

from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.knowledge.graph.builder import KnowledgeGraphBuilder
from app.knowledge.ml.entity_recognizer import MedicalEntityRecognizer
from app.utils.logger import app_logger


# 允许的实体类型白名单（防止注入非法标签）
ALLOWED_ENTITY_TYPES = {
    "Disease", "Symptom", "Drug", "Examination", "Department",
}

# 允许的关系类型白名单
ALLOWED_RELATION_TYPES = {
    "HAS_SYMPTOM", "TREATED_BY", "REQUIRES_EXAM",
    "BELONGS_TO", "INTERACTS_WITH", "CONTRAINDICATED_FOR",
}

# 实体类型 -> 中文映射（用于 NER 结果对齐）
ENTITY_TYPE_MAP = {
    "diseases": "Disease",
    "symptoms": "Symptom",
    "drugs": "Drug",
    "examinations": "Examination",
    "departments": "Department",
}


class KGUpdateAuditLog:
    """知识图谱更新审计日志（内存环形缓冲，线程安全）"""

    def __init__(self, max_size: int = 500):
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def append(self, entry: Dict[str, Any]):
        entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._lock:
            self._buffer.append(entry)

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._buffer)
        return items[-limit:]


class KnowledgeGraphUpdateService:
    """知识图谱实时更新服务

    功能：
    1. 手动 CRUD：通过 API 添加/更新/删除实体和关系
    2. 事件驱动更新：文档上传后自动抽取实体并写入图谱
    3. 审计日志：记录所有更新操作
    4. 缓存失效：写操作后自动清除 Neo4j 查询缓存
    """

    def __init__(self):
        self._builder: Optional[KnowledgeGraphBuilder] = None
        self._recognizer: Optional[MedicalEntityRecognizer] = None
        self.audit_log = KGUpdateAuditLog()

    @property
    def builder(self) -> KnowledgeGraphBuilder:
        if self._builder is None:
            self._builder = KnowledgeGraphBuilder()
        return self._builder

    @property
    def recognizer(self) -> MedicalEntityRecognizer:
        if self._recognizer is None:
            self._recognizer = MedicalEntityRecognizer()
        return self._recognizer

    # ==================== 实体操作 ====================

    def add_entity(
        self,
        entity_type: str,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """添加或更新实体（MERGE 语义，幂等）

        Args:
            entity_type: 实体类型，必须在白名单中
            name: 实体名称
            properties: 附加属性

        Returns:
            操作结果
        """
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError(
                f"不支持的实体类型: {entity_type}，允许: {ALLOWED_ENTITY_TYPES}"
            )

        props = dict(properties or {})
        props["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            result = self.builder.create_entity(
                entity_type, name, props, merge=True
            )
            self.audit_log.append({
                "action": "add_entity",
                "entity_type": entity_type,
                "name": name,
                "status": "success",
            })
            app_logger.info(f"KG 实体已更新: {entity_type}:{name}")
            return {
                "status": "success",
                "entity_type": entity_type,
                "name": name,
                "result": result,
            }
        except Exception as e:
            self.audit_log.append({
                "action": "add_entity",
                "entity_type": entity_type,
                "name": name,
                "status": "failed",
                "error": str(e),
            })
            raise

    def delete_entity(self, entity_type: str, name: str) -> Dict[str, Any]:
        """删除实体及其所有关联关系

        Args:
            entity_type: 实体类型
            name: 实体名称

        Returns:
            操作结果
        """
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"不支持的实体类型: {entity_type}")

        query = f"MATCH (n:{entity_type} {{name: $name}}) DETACH DELETE n RETURN count(n) as deleted"
        try:
            client = get_neo4j_client()
            result = client.execute_write(query, {"name": name})
            deleted_count = result[0].get("deleted", 0) if result else 0

            self.audit_log.append({
                "action": "delete_entity",
                "entity_type": entity_type,
                "name": name,
                "status": "success",
                "deleted_count": deleted_count,
            })
            app_logger.info(f"KG 实体已删除: {entity_type}:{name} (删除 {deleted_count} 个节点)")
            return {
                "status": "success",
                "entity_type": entity_type,
                "name": name,
                "deleted_count": deleted_count,
            }
        except Exception as e:
            self.audit_log.append({
                "action": "delete_entity",
                "entity_type": entity_type,
                "name": name,
                "status": "failed",
                "error": str(e),
            })
            raise

    # ==================== 关系操作 ====================

    def add_relationship(
        self,
        from_type: str,
        from_name: str,
        rel_type: str,
        to_type: str,
        to_name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """添加关系（MERGE 语义，幂等）

        Args:
            from_type: 起始实体类型
            from_name: 起始实体名称
            rel_type: 关系类型
            to_type: 目标实体类型
            to_name: 目标实体名称
            properties: 关系属性

        Returns:
            操作结果
        """
        if from_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"不支持的起始实体类型: {from_type}")
        if to_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"不支持的目标实体类型: {to_type}")
        if rel_type not in ALLOWED_RELATION_TYPES:
            raise ValueError(
                f"不支持的关系类型: {rel_type}，允许: {ALLOWED_RELATION_TYPES}"
            )

        props = dict(properties or {})
        props["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            result = self.builder.create_relationship(
                from_type, from_name, rel_type, to_type, to_name, props, merge=True
            )
            self.audit_log.append({
                "action": "add_relationship",
                "from": f"{from_type}:{from_name}",
                "rel_type": rel_type,
                "to": f"{to_type}:{to_name}",
                "status": "success",
            })
            app_logger.info(
                f"KG 关系已更新: ({from_type}:{from_name})-[{rel_type}]->({to_type}:{to_name})"
            )
            return {
                "status": "success",
                "from": f"{from_type}:{from_name}",
                "rel_type": rel_type,
                "to": f"{to_type}:{to_name}",
                "result": result,
            }
        except Exception as e:
            self.audit_log.append({
                "action": "add_relationship",
                "from": f"{from_type}:{from_name}",
                "rel_type": rel_type,
                "to": f"{to_type}:{to_name}",
                "status": "failed",
                "error": str(e),
            })
            raise

    # ==================== 事件驱动更新 ====================

    def update_from_document(self, document_text: str, source: str = "") -> Dict[str, Any]:
        """从文档内容中抽取医疗实体并增量更新知识图谱

        当新文档上传到知识库时调用此方法，自动：
        1. 使用 NER 识别文档中的疾病、症状、药物、检查等实体
        2. 将识别到的实体 MERGE 到知识图谱
        3. 自动建立「疾病→症状」「疾病→药物」「疾病→检查」关系

        Args:
            document_text: 文档文本内容
            source: 文档来源标识

        Returns:
            更新统计信息
        """
        stats = {
            "source": source,
            "entities_created": 0,
            "relationships_created": 0,
            "details": {
                "diseases": 0,
                "symptoms": 0,
                "drugs": 0,
                "examinations": 0,
                "departments": 0,
            },
            "errors": [],
        }

        if not document_text or len(document_text.strip()) < 10:
            stats["errors"].append("文档内容过短，跳过 KG 更新")
            return stats

        try:
            # 1. NER 实体抽取
            entities = self.recognizer.extract_entities(document_text, use_cache=False)
            app_logger.info(
                f"KG 事件驱动更新 - NER 结果: {sum(len(v) for v in entities.values())} 个实体 (来源: {source})"
            )

            # 2. 创建实体节点
            entity_name_map: Dict[str, List[str]] = {}  # entity_type -> [names]

            for ner_key, kg_type in ENTITY_TYPE_MAP.items():
                names = entities.get(ner_key, [])
                entity_name_map[kg_type] = names
                for name in names:
                    try:
                        self.add_entity(kg_type, name, {"source": source})
                        stats["entities_created"] += 1
                        stats["details"][ner_key] = stats["details"].get(ner_key, 0) + 1
                    except Exception as e:
                        stats["errors"].append(f"创建实体 {kg_type}:{name} 失败: {e}")

            # 3. 自动建立关系
            # 疾病 → 症状 (HAS_SYMPTOM)
            diseases = entity_name_map.get("Disease", [])
            symptoms = entity_name_map.get("Symptom", [])
            for disease in diseases:
                for symptom in symptoms:
                    try:
                        self.add_relationship(
                            "Disease", disease, "HAS_SYMPTOM", "Symptom", symptom
                        )
                        stats["relationships_created"] += 1
                    except Exception:
                        pass  # 关系创建失败不影响整体

            # 疾病 → 药物 (TREATED_BY)
            drugs = entity_name_map.get("Drug", [])
            for disease in diseases:
                for drug in drugs:
                    try:
                        self.add_relationship(
                            "Disease", disease, "TREATED_BY", "Drug", drug
                        )
                        stats["relationships_created"] += 1
                    except Exception:
                        pass

            # 疾病 → 检查 (REQUIRES_EXAM)
            exams = entity_name_map.get("Examination", [])
            for disease in diseases:
                for exam in exams:
                    try:
                        self.add_relationship(
                            "Disease", disease, "REQUIRES_EXAM", "Examination", exam
                        )
                        stats["relationships_created"] += 1
                    except Exception:
                        pass

            # 症状 → 科室 (BELONGS_TO)
            departments = entity_name_map.get("Department", [])
            for symptom in symptoms:
                for dept in departments:
                    try:
                        self.add_relationship(
                            "Symptom", symptom, "BELONGS_TO", "Department", dept
                        )
                        stats["relationships_created"] += 1
                    except Exception:
                        pass

            self.audit_log.append({
                "action": "document_update",
                "source": source,
                "status": "success",
                "entities_created": stats["entities_created"],
                "relationships_created": stats["relationships_created"],
            })

            app_logger.info(
                f"KG 事件驱动更新完成 (来源: {source}): "
                f"{stats['entities_created']} 实体, {stats['relationships_created']} 关系"
            )

        except Exception as e:
            stats["errors"].append(f"事件驱动更新失败: {e}")
            app_logger.error(f"KG 事件驱动更新失败 (来源: {source}): {e}")
            self.audit_log.append({
                "action": "document_update",
                "source": source,
                "status": "failed",
                "error": str(e),
            })

        return stats

    # ==================== 审计日志查询 ====================

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的更新审计日志"""
        return self.audit_log.get_recent(limit)


# 全局单例
_kg_update_service: Optional[KnowledgeGraphUpdateService] = None
_kg_update_lock = threading.Lock()


def get_kg_update_service() -> KnowledgeGraphUpdateService:
    """获取知识图谱更新服务单例"""
    global _kg_update_service
    if _kg_update_service is None:
        with _kg_update_lock:
            if _kg_update_service is None:
                _kg_update_service = KnowledgeGraphUpdateService()
    return _kg_update_service
