"""医生Agent"""
from typing import Dict, Any, Optional
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.agents.base import BaseAgent
from app.agents.tools.rag_tool import RAGTool
from app.agents.tools.knowledge_graph_tool import KnowledgeGraphTool
from app.agents.tools.diagnosis_tool import DiagnosisTool
from app.knowledge.ml.entity_recognizer import MedicalEntityRecognizer
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
        
        # 实体识别器
        self.entity_recognizer = MedicalEntityRecognizer()
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return PromptTemplate.MEDICAL_CONSULTATION_SYSTEM
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理医疗咨询"""
        start_time = time.time()
        trace_id = input_data.get("trace_id")
        
        try:
            question = input_data.get("question", "")
            context = input_data.get("context", {})
            consultation_type = input_data.get("type", "general")  # general, diagnosis, drug
            
            app_logger.info(f"医生Agent处理咨询: {question[:50]}...")
            
            # 根据咨询类型选择处理方式
            if consultation_type == "diagnosis":
                result = self._handle_diagnosis(question, context, trace_id=trace_id)
            elif consultation_type == "drug":
                result = self._handle_drug_consultation(question, context, trace_id=trace_id)
            else:
                result = self._handle_general_consultation(question, context, trace_id=trace_id)
            
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
    
    def _format_history(self, context: Dict) -> str:
        """格式化历史记录"""
        history = context.get("history", [])
        if not history:
            return ""
        
        history_text = "\n【对话历史】\n"
        for msg in history:
            role = "用户" if msg.get("role") == "user" else "AI助手"
            content = msg.get("content", "")
            # 简单的截断，防止历史记录过长
            if len(content) > 200:
                content = content[:200] + "..."
            history_text += f"{role}: {content}\n"
        
        return history_text + "\n"

    def _handle_general_consultation(self, question: str, context: Dict, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """处理一般咨询（并行优化）"""
        tools_used = []
        
        # 并行执行RAG检索和KG查询
        rag_result = {"results": []}
        rag_context = ""
        kg_context = ""
        
        def execute_rag():
            """执行RAG检索"""
            try:
                result = self.rag_tool.execute(question, top_k=5)
                return ("rag", result, self.rag_tool.format_context(result) if result.get("results") else "")
            except Exception as e:
                app_logger.warning(f"RAG检索失败: {e}")
                return ("rag", {"results": []}, "")
        
        def execute_kg():
            """执行知识图谱查询（从RAG结果中提取，或使用KG工具）"""
            try:
                # 方法1: 从RAG结果中提取知识图谱相关结果
                # RAG检索已经包含了知识图谱检索（通过AdvancedRAG）
                rag_result = self.rag_tool.execute(question, top_k=5)
                kg_results = [
                    r for r in rag_result.get("results", [])
                    if r.get("retrieval_method") == "knowledge_graph" or 
                       r.get("source") == "knowledge_graph"
                ]
                
                if kg_results:
                    kg_context = "\n".join([
                        f"- {r.get('text', '')}" 
                        for r in kg_results[:3]
                    ])
                    return ("kg", kg_results, kg_context)
                
                # 方法2: 如果RAG中没有KG结果，尝试直接使用KG工具
                # 使用实体识别进行智能查询
                try:
                    from app.knowledge.rag.kg_retriever import KnowledgeGraphRetriever
                    kg_retriever = KnowledgeGraphRetriever()
                    kg_results = kg_retriever.retrieve(question, top_k=3)
                    
                    if kg_results:
                        kg_context = "\n".join([
                            f"- {r.get('text', '')}" 
                            for r in kg_results[:3]
                        ])
                        return ("kg", kg_results, kg_context)
                except Exception as kg_error:
                    app_logger.debug(f"直接KG查询失败: {kg_error}")
                
                return ("kg", None, "")
            except Exception as e:
                app_logger.warning(f"知识图谱查询失败: {e}")
                return ("kg", None, "")
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(execute_rag): "rag",
                executor.submit(execute_kg): "kg"
            }
            
            for future in as_completed(futures):
                try:
                    tool_type, result, formatted_context = future.result()
                    if tool_type == "rag":
                        rag_result = result
                        rag_context = formatted_context
                        if rag_result.get("results"):
                            tools_used.append("rag_search")
                    elif tool_type == "kg":
                        if result:
                            kg_context = formatted_context
                            tools_used.append("knowledge_graph_query")
                except Exception as e:
                    app_logger.warning(f"并行执行失败: {e}")
        
        # 整合上下文
        history_text = self._format_history(context)
        base_context = f"{rag_context}\n\n{kg_context}" if kg_context else rag_context
        full_context = f"{history_text}{base_context}" if history_text else base_context
        
        # 4. 生成回答
        prompt = PromptTemplate.format_medical_prompt(full_context, question)
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        # 无检索结果时添加用户提示
        answer = self.format_answer_with_fallback(answer, full_context)
        
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
    
    def _handle_diagnosis(self, question: str, context: Dict, trace_id: Optional[str] = None) -> Dict[str, Any]:
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
        try:
            rag_result = self.rag_tool.execute(question, top_k=3)
            tools_used.append("rag_search")
            rag_context = self.rag_tool.format_context(rag_result) if rag_result.get("results") else ""
        except Exception as e:
            app_logger.warning(f"RAG检索失败: {e}")
            rag_result = {"results": []}
            rag_context = ""
        
        # 4. 整合上下文
        history_text = self._format_history(context)
        base_context = f"{rag_context}\n\n{kg_context}" if kg_context else rag_context
        full_context = f"{history_text}{base_context}" if history_text else base_context
        
        # 5. 生成诊断建议
        prompt = PromptTemplate.format_diagnosis_prompt(question, full_context)
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=PromptTemplate.DIAGNOSIS_ASSISTANT_SYSTEM,
            temperature=0.7
        )
        
        # 6. 无检索结果时添加用户提示
        answer = self.format_answer_with_fallback(answer, full_context)
        
        # 7. 添加风险提示
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
    
    def _handle_drug_consultation(self, question: str, context: Dict, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """处理用药咨询"""
        tools_used = []
        
        # 1. 提取药物名称（使用NER）
        drug_names = []
        try:
            entities = self.entity_recognizer.extract_entities(question)
            drug_names = entities.get("drugs", [])
        except Exception as e:
            app_logger.warning(f"药物实体识别失败: {e}")
        
        # 2. 查询药物信息
        kg_context = ""
        found_drugs = []
        
        if drug_names:
            kg_context = "知识图谱药物信息:\n"
            for drug_name in drug_names:
                try:
                    drug_info = self.kg_tool.execute("get_drug_info", drug_name=drug_name)
                    tools_used.append("knowledge_graph_query")
                    
                    if drug_info.get("found"):
                        found_drugs.append(drug_name)
                        drug = drug_info.get("drug", {})
                        kg_context += f"- 药物: {drug.get('name', drug_name)}\n"
                        
                        if drug_info.get("contraindications"):
                            kg_context += "  禁忌症: " + ", ".join([c.get('disease', '') for c in drug_info["contraindications"]]) + "\n"
                            
                        if drug_info.get("interactions"):
                            kg_context += "  相互作用: " + ", ".join([i.get('interacting_drug', '') for i in drug_info["interactions"]]) + "\n"
                except Exception as e:
                    app_logger.warning(f"查询药物 {drug_name} 失败: {e}")
        
        # 3. RAG检索用药指南
        try:
            rag_result = self.rag_tool.execute(question, top_k=3)
            tools_used.append("rag_search")
            rag_context = self.rag_tool.format_context(rag_result) if rag_result.get("results") else ""
        except Exception as e:
            app_logger.warning(f"RAG检索失败: {e}")
            rag_result = {"results": []}
            rag_context = ""
        
        # 4. 整合上下文
        history_text = self._format_history(context)
        base_context = f"{rag_context}\n\n{kg_context}" if kg_context else rag_context
        full_context = f"{history_text}{base_context}" if history_text else base_context
        
        # 5. 生成用药建议
        # 如果有明确的药物，传递给Prompt
        drug_info_str = ", ".join(found_drugs) if found_drugs else (drug_names[0] if drug_names else None)
        
        prompt = PromptTemplate.format_drug_prompt(question, drug_info=drug_info_str, context=full_context)
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=PromptTemplate.DRUG_CONSULTATION_SYSTEM,
            temperature=0.7
        )
        
        # 6. 无检索结果时添加用户提示
        answer = self.format_answer_with_fallback(answer, full_context)
        
        return {
            "answer": answer,
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": tools_used
        }

