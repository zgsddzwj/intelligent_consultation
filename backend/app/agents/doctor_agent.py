"""医生Agent"""
from typing import Dict, Any
import time
from app.agents.base import BaseAgent
from app.agents.tools.rag_tool import RAGTool
from app.agents.tools.knowledge_graph_tool import KnowledgeGraphTool
from app.agents.tools.diagnosis_tool import DiagnosisTool
from app.services.llm_service import PromptTemplate
from app.utils.logger import app_logger


class DoctorAgent(BaseAgent):
    """医生Agent - 提供医疗诊断建议、用药咨询等"""
    
    def __init__(self):
        super().__init__(
            name="doctor",
            description="专业的AI医生助手，提供诊断建议、用药咨询、检查建议"
        )
        
        # 添加工具
        self.rag_tool = RAGTool()
        self.kg_tool = KnowledgeGraphTool()
        self.diagnosis_tool = DiagnosisTool()
        
        self.add_tool(self.rag_tool)
        self.add_tool(self.kg_tool)
        self.add_tool(self.diagnosis_tool)
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return PromptTemplate.MEDICAL_CONSULTATION_SYSTEM
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理医疗咨询"""
        start_time = time.time()
        
        try:
            question = input_data.get("question", "")
            context = input_data.get("context", {})
            consultation_type = input_data.get("type", "general")  # general, diagnosis, drug
            
            app_logger.info(f"医生Agent处理咨询: {question[:50]}...")
            
            # 根据咨询类型选择处理方式
            if consultation_type == "diagnosis":
                result = self._handle_diagnosis(question, context)
            elif consultation_type == "drug":
                result = self._handle_drug_consultation(question, context)
            else:
                result = self._handle_general_consultation(question, context)
            
            execution_time = time.time() - start_time
            
            # 记录日志
            tools_used = result.get("tools_used", [])
            self.log_execution(input_data, result, execution_time, tools_used)
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            app_logger.error(f"医生Agent处理失败: {e}")
            execution_time = time.time() - start_time
            return {
                "answer": f"处理咨询时发生错误: {str(e)}",
                "error": str(e),
                "execution_time": execution_time,
                "tools_used": []
            }
    
    def _handle_general_consultation(self, question: str, context: Dict) -> Dict[str, Any]:
        """处理一般咨询"""
        tools_used = []
        
        # 1. RAG检索
        rag_result = self.rag_tool.execute(question, top_k=5)
        tools_used.append("rag_search")
        rag_context = self.rag_tool.format_context(rag_result)
        
        # 2. 提取可能的疾病/药物实体，查询知识图谱
        kg_context = ""
        # 这里可以添加实体识别逻辑，暂时简化
        if "高血压" in question or "血压" in question:
            disease_info = self.kg_tool.execute("get_disease_info", disease_name="高血压")
            tools_used.append("knowledge_graph_query")
            if disease_info.get("found"):
                kg_context = self.kg_tool.format_disease_info(disease_info)
        
        # 3. 整合上下文
        full_context = f"{rag_context}\n\n{kg_context}" if kg_context else rag_context
        
        # 4. 生成回答
        prompt = PromptTemplate.format_medical_prompt(full_context, question)
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        # 5. 添加来源信息
        sources = []
        if rag_result.get("results"):
            sources = [r.get("source") for r in rag_result["results"]]
        
        return {
            "answer": answer,
            "sources": sources,
            "context_used": full_context[:500],  # 截取前500字符
            "tools_used": tools_used
        }
    
    def _handle_diagnosis(self, question: str, context: Dict) -> Dict[str, Any]:
        """处理诊断咨询"""
        tools_used = []
        
        # 1. 诊断辅助工具分析症状
        diagnosis_result = self.diagnosis_tool.execute(question)
        tools_used.append("diagnosis_assistant")
        risk_level = diagnosis_result.get("risk_level", "low")
        
        # 2. 根据症状查找可能的疾病
        symptoms = diagnosis_result.get("symptom_keywords", [])
        kg_context = ""
        if symptoms:
            disease_result = self.kg_tool.execute(
                "find_diseases_by_symptoms",
                symptoms=symptoms
            )
            tools_used.append("knowledge_graph_query")
            if disease_result.get("diseases"):
                kg_context = "可能的疾病:\n"
                for disease in disease_result["diseases"][:5]:
                    kg_context += f"- {disease.get('disease', '')}\n"
        
        # 3. RAG检索相关诊断信息
        rag_result = self.rag_tool.execute(question, top_k=3)
        tools_used.append("rag_search")
        rag_context = self.rag_tool.format_context(rag_result)
        
        # 4. 整合上下文
        full_context = f"{rag_context}\n\n{kg_context}" if kg_context else rag_context
        
        # 5. 生成诊断建议
        prompt = PromptTemplate.format_diagnosis_prompt(question, full_context)
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=PromptTemplate.DIAGNOSIS_ASSISTANT_SYSTEM,
            temperature=0.7
        )
        
        # 6. 添加风险提示
        if risk_level in ["high", "critical"]:
            risk_recommendation = self.diagnosis_tool.get_risk_recommendation(risk_level)
            answer += f"\n\n⚠️ 风险提示: {risk_recommendation}"
        
        return {
            "answer": answer,
            "risk_level": risk_level,
            "diagnosis_analysis": diagnosis_result,
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": tools_used
        }
    
    def _handle_drug_consultation(self, question: str, context: Dict) -> Dict[str, Any]:
        """处理用药咨询"""
        tools_used = []
        
        # 1. 提取药物名称（简化处理）
        drug_name = None
        if "高血压" in question or "降压" in question:
            drug_name = "高血压药物"  # 示例
        
        # 2. 查询药物信息
        kg_context = ""
        if drug_name:
            drug_info = self.kg_tool.execute("get_drug_info", drug_name=drug_name)
            tools_used.append("knowledge_graph_query")
            if drug_info.get("found"):
                drug = drug_info.get("drug", {})
                kg_context = f"药物信息: {drug.get('name', '')}\n"
                if drug_info.get("contraindications"):
                    kg_context += "禁忌症:\n"
                    for contra in drug_info["contraindications"]:
                        kg_context += f"- {contra.get('disease', '')}\n"
        
        # 3. RAG检索用药指南
        rag_result = self.rag_tool.execute(question, top_k=3)
        tools_used.append("rag_search")
        rag_context = self.rag_tool.format_context(rag_result)
        
        # 4. 整合上下文
        full_context = f"{rag_context}\n\n{kg_context}" if kg_context else rag_context
        
        # 5. 生成用药建议
        prompt = PromptTemplate.format_drug_prompt(question, drug_info=drug_name, context=full_context)
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=PromptTemplate.DRUG_CONSULTATION_SYSTEM,
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": tools_used
        }

