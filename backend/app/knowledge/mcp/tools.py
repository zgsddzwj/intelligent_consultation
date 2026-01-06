"""MCP工具定义"""
from typing import Dict, Any, List
from app.agents.tools.rag_tool import RAGTool
from app.agents.tools.knowledge_graph_tool import KnowledgeGraphTool
from app.agents.tools.diagnosis_tool import DiagnosisTool
from app.utils.logger import app_logger


class MCPTools:
    """MCP工具集"""
    
    def __init__(self):
        self.rag_tool = RAGTool()
        self.kg_tool = KnowledgeGraphTool()
        self.diagnosis_tool = DiagnosisTool()
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有工具定义"""
        return [
            {
                "name": "query_knowledge_graph",
                "description": "查询医疗知识图谱，获取疾病、症状、药物等实体关系",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["get_disease_info", "get_drug_info", "get_drug_interactions", "find_diseases_by_symptoms"],
                            "description": "操作类型"
                        },
                        "disease_name": {
                            "type": "string",
                            "description": "疾病名称（用于get_disease_info操作）"
                        },
                        "drug_name": {
                            "type": "string",
                            "description": "药物名称（用于get_drug_info和get_drug_interactions操作）"
                        },
                        "symptoms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "症状列表（用于find_diseases_by_symptoms操作）"
                        }
                    },
                    "required": ["operation"]
                }
            },
            {
                "name": "search_medical_literature",
                "description": "检索医学文献和文档，获取相关医疗信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_drug_info",
                "description": "获取药物详细信息，包括适应症、禁忌、相互作用等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "药物名称"
                        }
                    },
                    "required": ["drug_name"]
                }
            },
            {
                "name": "check_drug_interaction",
                "description": "检查药物相互作用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "drug_name": {
                            "type": "string",
                            "description": "药物名称"
                        }
                    },
                    "required": ["drug_name"]
                }
            },
            {
                "name": "get_diagnosis_suggestions",
                "description": "根据症状获取诊断建议",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symptoms": {
                            "type": "string",
                            "description": "症状描述"
                        }
                    },
                    "required": ["symptoms"]
                }
            },
            {
                "name": "log_consultation",
                "description": "记录咨询日志",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "consultation_id": {
                            "type": "integer",
                            "description": "咨询ID"
                        },
                        "agent_type": {
                            "type": "string",
                            "description": "Agent类型"
                        },
                        "input_data": {
                            "type": "object",
                            "description": "输入数据"
                        },
                        "output_data": {
                            "type": "object",
                            "description": "输出数据"
                        }
                    },
                    "required": ["consultation_id", "agent_type"]
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            if tool_name == "query_knowledge_graph":
                operation = parameters.get("operation")
                return self.kg_tool.execute(operation, **parameters)
            
            elif tool_name == "search_medical_literature":
                query = parameters.get("query")
                top_k = parameters.get("top_k", 5)
                return self.rag_tool.execute(query, top_k=top_k)
            
            elif tool_name == "get_drug_info":
                drug_name = parameters.get("drug_name")
                return self.kg_tool.execute("get_drug_info", drug_name=drug_name)
            
            elif tool_name == "check_drug_interaction":
                drug_name = parameters.get("drug_name")
                return self.kg_tool.execute("get_drug_interactions", drug_name=drug_name)
            
            elif tool_name == "get_diagnosis_suggestions":
                symptoms = parameters.get("symptoms")
                return self.diagnosis_tool.execute(symptoms)
            
            elif tool_name == "log_consultation":
                # 这里可以保存到数据库
                app_logger.info(f"记录咨询日志: {parameters}")
                return {"status": "logged", "consultation_id": parameters.get("consultation_id")}
            
            else:
                raise ValueError(f"未知工具: {tool_name}")
                
        except Exception as e:
            app_logger.error(f"工具执行失败: {tool_name}, {e}")
            return {"error": str(e), "tool": tool_name}

