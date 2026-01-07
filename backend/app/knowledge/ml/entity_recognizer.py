"""医疗实体识别器 - 使用LLM进行NER"""
from typing import List, Dict, Any, Optional
from app.services.llm_service import llm_service
from app.utils.logger import app_logger
import json
import re


class MedicalEntityRecognizer:
    """医疗实体识别器 - 使用LLM进行命名实体识别"""
    
    ENTITY_TYPES = {
        "diseases": "疾病",
        "symptoms": "症状", 
        "drugs": "药物",
        "examinations": "检查",
        "departments": "科室"
    }
    
    def __init__(self):
        self.cache = {}  # 简单的缓存机制
    
    def extract_entities(self, query: str, use_cache: bool = True) -> Dict[str, List[str]]:
        """
        从查询中提取医疗实体
        
        Args:
            query: 查询文本
            use_cache: 是否使用缓存
        
        Returns:
            实体字典，包含diseases, symptoms, drugs, examinations, departments
        """
        # 检查缓存
        if use_cache and query in self.cache:
            return self.cache[query]
        
        entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": [],
            "departments": []
        }
        
        try:
            # 使用LLM进行实体识别
            prompt = self._build_ner_prompt(query)
            response = llm_service.generate(
                prompt=prompt,
                system_prompt="你是一个专业的医疗实体识别助手，擅长从医疗相关文本中准确提取实体。",
                temperature=0.1,  # 低温度保证稳定性
                max_tokens=500
            )
            
            # 解析LLM返回的JSON
            entities = self._parse_llm_response(response, query)
            
            # 缓存结果
            if use_cache:
                self.cache[query] = entities
            
            app_logger.debug(f"实体识别完成: {query} -> {entities}")
            return entities
            
        except Exception as e:
            app_logger.warning(f"LLM实体识别失败，使用回退策略: {e}")
            # 回退到简单匹配
            return self._fallback_extraction(query)
    
    def _build_ner_prompt(self, query: str) -> str:
        """构建NER提示词"""
        return f"""请从以下医疗咨询问题中提取所有医疗相关实体，并按类型分类。

问题：{query}

请以JSON格式返回，格式如下：
{{
    "diseases": ["疾病名称1", "疾病名称2"],
    "symptoms": ["症状名称1", "症状名称2"],
    "drugs": ["药物名称1", "药物名称2"],
    "examinations": ["检查项目1", "检查项目2"],
    "departments": ["科室名称1", "科室名称2"]
}}

要求：
1. 只提取明确提到的实体，不要推测
2. 实体名称要完整准确
3. 如果某个类型没有实体，返回空数组
4. 只返回JSON，不要其他文字

JSON:"""
    
    def _parse_llm_response(self, response: str, query: str) -> Dict[str, List[str]]:
        """解析LLM返回的JSON"""
        entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": [],
            "departments": []
        }
        
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # 验证和清理实体
                for entity_type in entities.keys():
                    if entity_type in parsed and isinstance(parsed[entity_type], list):
                        # 去重和过滤空值
                        entities[entity_type] = list(set([
                            str(e).strip() 
                            for e in parsed[entity_type] 
                            if e and str(e).strip()
                        ]))
            
        except json.JSONDecodeError as e:
            app_logger.warning(f"JSON解析失败: {e}, 响应: {response[:200]}")
        except Exception as e:
            app_logger.warning(f"解析LLM响应失败: {e}")
        
        return entities
    
    def _fallback_extraction(self, query: str) -> Dict[str, List[str]]:
        """回退策略：使用关键词匹配"""
        entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": [],
            "departments": []
        }
        
        # 常见医疗关键词模式
        disease_patterns = [
            r'([\u4e00-\u9fa5]+(?:病|症|炎|癌|瘤|症候群))',
            r'(高血压|糖尿病|心脏病|癌症|肿瘤|感冒|发烧)'
        ]
        
        symptom_patterns = [
            r'([\u4e00-\u9fa5]*(?:痛|疼|热|烧|咳|吐|泻|晕|乏|累))',
            r'(头痛|发热|咳嗽|疼痛|乏力|头晕|恶心|呕吐)'
        ]
        
        drug_patterns = [
            r'([\u4e00-\u9fa5]+(?:药|片|胶囊|注射液|颗粒))',
            r'(阿司匹林|布洛芬|青霉素|头孢)'
        ]
        
        exam_patterns = [
            r'([\u4e00-\u9fa5]*(?:检查|化验|检测|CT|MRI|X光|B超))',
            r'(血常规|尿常规|心电图|CT|MRI)'
        ]
        
        # 提取实体
        for pattern in disease_patterns:
            matches = re.findall(pattern, query)
            entities["diseases"].extend(matches)
        
        for pattern in symptom_patterns:
            matches = re.findall(pattern, query)
            entities["symptoms"].extend(matches)
        
        for pattern in drug_patterns:
            matches = re.findall(pattern, query)
            entities["drugs"].extend(matches)
        
        for pattern in exam_patterns:
            matches = re.findall(pattern, query)
            entities["examinations"].extend(matches)
        
        # 去重
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def extract_with_kg_validation(self, query: str, kg_client) -> Dict[str, List[str]]:
        """
        提取实体并使用知识图谱验证
        
        Args:
            query: 查询文本
            kg_client: Neo4j客户端
        
        Returns:
            验证后的实体字典
        """
        # 先使用LLM提取
        entities = self.extract_entities(query)
        
        if not kg_client:
            return entities
        
        # 使用知识图谱验证实体是否存在
        validated_entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": [],
            "departments": []
        }
        
        try:
            # 验证疾病
            for disease in entities["diseases"]:
                query_str = "MATCH (d:Disease) WHERE d.name CONTAINS $name RETURN d.name LIMIT 1"
                result = kg_client.execute_query(query_str, {"name": disease})
                if result:
                    validated_entities["diseases"].append(disease)
            
            # 验证症状
            for symptom in entities["symptoms"]:
                query_str = "MATCH (s:Symptom) WHERE s.name CONTAINS $name RETURN s.name LIMIT 1"
                result = kg_client.execute_query(query_str, {"name": symptom})
                if result:
                    validated_entities["symptoms"].append(symptom)
            
            # 验证药物
            for drug in entities["drugs"]:
                query_str = "MATCH (d:Drug) WHERE d.name CONTAINS $name RETURN d.name LIMIT 1"
                result = kg_client.execute_query(query_str, {"name": drug})
                if result:
                    validated_entities["drugs"].append(drug)
            
            # 验证检查
            for exam in entities["examinations"]:
                query_str = "MATCH (e:Examination) WHERE e.name CONTAINS $name RETURN e.name LIMIT 1"
                result = kg_client.execute_query(query_str, {"name": exam})
                if result:
                    validated_entities["examinations"].append(exam)
            
        except Exception as e:
            app_logger.warning(f"知识图谱验证失败: {e}")
            return entities  # 返回未验证的结果
        
        return validated_entities

