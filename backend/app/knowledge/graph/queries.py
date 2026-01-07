"""Cypher查询模板"""
from typing import Dict, List, Optional


class CypherQueries:
    """Cypher查询模板类"""
    
    @staticmethod
    def create_disease(name: str, icd10: Optional[str] = None, **properties) -> str:
        """创建疾病节点"""
        props = {"name": name}
        if icd10:
            props["icd10"] = icd10
        props.update(properties)
        props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])
        return f"CREATE (d:Disease {{{props_str}}}) RETURN d"
    
    @staticmethod
    def find_disease_by_name(name: str) -> str:
        """根据名称查找疾病"""
        return "MATCH (d:Disease {name: $name}) RETURN d"
    
    @staticmethod
    def find_disease_symptoms(disease_name: str) -> str:
        """查找疾病的症状"""
        return """
        MATCH (d:Disease {name: $disease_name})-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN s.name as symptom, s.severity as severity
        """
    
    @staticmethod
    def find_disease_drugs(disease_name: str) -> str:
        """查找疾病的治疗药物"""
        return """
        MATCH (d:Disease {name: $disease_name})-[:TREATED_BY]->(dr:Drug)
        RETURN dr.name as drug, dr.generic_name as generic_name, 
               dr.dosage_form as dosage_form
        """
    
    @staticmethod
    def find_disease_examinations(disease_name: str) -> str:
        """查找疾病需要的检查"""
        return """
        MATCH (d:Disease {name: $disease_name})-[:REQUIRES_EXAM]->(e:Examination)
        RETURN e.name as examination, e.type as type, e.reference_range as reference_range
        """
    
    @staticmethod
    def find_drug_interactions(drug_name: str) -> str:
        """查找药物相互作用"""
        return """
        MATCH (d1:Drug {name: $drug_name})-[r:INTERACTS_WITH]-(d2:Drug)
        RETURN d2.name as interacting_drug, r.interaction_type as type, 
               r.severity as severity, r.description as description
        """
    
    @staticmethod
    def find_drug_contraindications(drug_name: str) -> str:
        """查找药物禁忌"""
        return """
        MATCH (dr:Drug {name: $drug_name})-[:CONTRAINDICATED_FOR]->(d:Disease)
        RETURN d.name as disease, d.icd10 as icd10
        """
    
    @staticmethod
    def find_symptoms_by_department(dept_name: str) -> str:
        """根据科室查找症状"""
        return """
        MATCH (s:Symptom)-[:BELONGS_TO]->(dept:Department {name: $dept_name})
        RETURN s.name as symptom, s.severity as severity
        """
    
    @staticmethod
    def find_diseases_by_symptoms(symptom_names: List[str]) -> str:
        """根据症状查找可能的疾病"""
        return f"""
        MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
        WHERE s.name IN {symptom_names}
        WITH d, count(s) as symptom_count
        WHERE symptom_count >= {len(symptom_names) // 2 + 1}
        RETURN d.name as disease, d.icd10 as icd10, symptom_count
        ORDER BY symptom_count DESC
        LIMIT 10
        """
    
    @staticmethod
    def get_department_graph(dept_name: str, depth: int = 2) -> str:
        """获取科室知识图谱"""
        return f"""
        MATCH path = (dept:Department {{name: $dept_name}})
        <-[:BELONGS_TO]-(s:Symptom)
        -[:HAS_SYMPTOM*0..{depth}]-(d:Disease)
        -[r*0..{depth}]-(related)
        WHERE related:Drug OR related:Examination OR related:Symptom OR related:Department
        WITH dept, s, d, related, r, path
        LIMIT 200
        RETURN dept, s, d, related, r, path
        """
    
    @staticmethod
    def get_all_graph_data(limit: int = 200) -> str:
        """获取所有图谱数据"""
        return f"""
        MATCH (dept:Department)<-[:BELONGS_TO]-(s:Symptom)
        -[:HAS_SYMPTOM]-(d:Disease)
        -[:TREATED_BY]->(drug:Drug)
        OPTIONAL MATCH (d)-[:REQUIRES_EXAM]->(exam:Examination)
        WITH dept, s, d, drug, exam
        LIMIT {limit}
        RETURN dept, s, d, drug, exam
        """
    
    @staticmethod
    def create_relationship(from_type: str, from_name: str, 
                           rel_type: str, to_type: str, to_name: str,
                           properties: Optional[Dict] = None, merge: bool = True) -> str:
        """创建关系（默认使用MERGE避免重复）"""
        rel_props = ""
        if properties:
            props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
            rel_props = f" {{{props_str}}}"
        
        if merge:
            # 使用MERGE避免重复创建关系
            if properties:
                set_props = ", ".join([f"r.{k} = ${k}" for k in properties.keys()])
                return f"""
                MATCH (a:{from_type} {{name: $from_name}})
                MATCH (b:{to_type} {{name: $to_name}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET {set_props}
                RETURN r
                """
            else:
                return f"""
                MATCH (a:{from_type} {{name: $from_name}})
                MATCH (b:{to_type} {{name: $to_name}})
                MERGE (a)-[r:{rel_type}]->(b)
                RETURN r
                """
        else:
            # 使用CREATE（不推荐，可能重复）
            return f"""
            MATCH (a:{from_type} {{name: $from_name}})
            MATCH (b:{to_type} {{name: $to_name}})
            CREATE (a)-[r:{rel_type}{rel_props}]->(b)
            RETURN r
            """
