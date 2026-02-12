"""健康管家Agent"""
from typing import Dict, Any, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.agents.base import BaseAgent
from app.agents.tools.rag_tool import RAGTool
from app.agents.tools.knowledge_graph_tool import KnowledgeGraphTool
from app.knowledge.ml.entity_recognizer import MedicalEntityRecognizer
from app.services.llm_service import PromptTemplate
from app.utils.logger import app_logger


class HealthManagerAgent(BaseAgent):
    """健康管家Agent - 提供慢病管理、健康计划等服务"""
    
    def __init__(self):
        super().__init__(
            name="health_manager",
            description="健康管家，提供慢病管理计划、生活方式建议、健康数据追踪"
        )
        
        # 添加工具
        self.rag_tool = RAGTool()
        self.kg_tool = KnowledgeGraphTool()
        
        self.add_tool(self.rag_tool)
        self.add_tool(self.kg_tool)
        
        # 实体识别器
        self.entity_recognizer = MedicalEntityRecognizer()
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return PromptTemplate.HEALTH_MANAGER_SYSTEM
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康管理咨询"""
        start_time = time.time()
        trace_id = input_data.get("trace_id")
        
        try:
            question = input_data.get("question", "")
            context = input_data.get("context", {})
            user_profile = input_data.get("user_profile", {})
            # 兼容旧的调用方式，如果context里有user_profile也可以读取
            if not user_profile and "user_profile" in context:
                user_profile = context["user_profile"]
                
            request_type = input_data.get("type", "general")  # general, plan, tracking
            
            app_logger.info(f"健康管家Agent处理请求: {question[:50]}...")
            
            if request_type == "plan":
                result = self._create_health_plan(question, user_profile, context, trace_id)
            elif request_type == "tracking":
                result = self._handle_health_tracking(question, user_profile, context, trace_id)
            else:
                result = self._handle_general_health_consultation(question, context, trace_id)
            
            execution_time = time.time() - start_time
            tools_used = result.get("tools_used", [])
            self.log_execution(input_data, result, execution_time, tools_used)
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            app_logger.error(f"健康管家Agent处理失败: {e}")
            execution_time = time.time() - start_time
            return {
                "answer": f"处理请求时发生错误: {str(e)}",
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
            if len(content) > 200:
                content = content[:200] + "..."
            history_text += f"{role}: {content}\n"
        
        return history_text + "\n"
    
    def _handle_general_health_consultation(self, question: str, context: Dict, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """处理一般健康咨询（并行优化）"""
        tools_used = []
        rag_result = {"results": []}
        rag_context = ""
        
        # 1. 并行执行RAG和实体识别
        def execute_rag():
            try:
                result = self.rag_tool.execute(question, top_k=3)
                return ("rag", result, self.rag_tool.format_context(result) if result.get("results") else "")
            except Exception as e:
                app_logger.warning(f"RAG检索失败: {e}")
                return ("rag", {"results": []}, "")

        def execute_kg_enrichment():
            """通过实体识别增强KG查询"""
            try:
                entities = self.entity_recognizer.extract_entities(question)
                diseases = entities.get("diseases", [])
                
                kg_context_parts = []
                found_info = False
                
                for disease in diseases:
                    info = self.kg_tool.execute("get_disease_info", disease_name=disease)
                    if info.get("found"):
                        formatted = self.kg_tool.format_disease_info(info)
                        kg_context_parts.append(formatted)
                        found_info = True
                
                return ("kg", found_info, "\n\n".join(kg_context_parts))
            except Exception as e:
                app_logger.warning(f"KG增强查询失败: {e}")
                return ("kg", False, "")

        kg_context = ""
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(execute_rag): "rag",
                executor.submit(execute_kg_enrichment): "kg"
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
                        if result: # found_info is True
                            kg_context = formatted_context
                            tools_used.append("knowledge_graph_query")
                except Exception as e:
                    app_logger.warning(f"任务执行失败: {e}")

        # 2. 整合上下文
        history_text = self._format_history(context)
        # 组合 RAG 和 KG 上下文
        combined_context = ""
        if rag_context:
            combined_context += f"【相关文档】\n{rag_context}\n"
        if kg_context:
            combined_context += f"\n【知识图谱信息】\n{kg_context}\n"
            
        full_context = f"{history_text}{combined_context}" if history_text else combined_context
        
        # 3. 生成回答
        prompt = f"""基于以下健康管理信息，回答用户的问题：

{full_context}

用户问题：{question}

请提供专业、实用的健康管理建议。"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        # 4. Fallback处理
        answer = self.format_answer_with_fallback(answer, full_context)
        
        return {
            "answer": answer,
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": tools_used
        }
    
    def _create_health_plan(self, question: str, profile: Dict, context: Dict, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """创建健康计划"""
        tools_used = []
        rag_result = {"results": []}
        rag_context = ""
        kg_context = ""
        
        # 1. 并行执行RAG和实体识别
        def execute_rag():
            try:
                # 针对计划生成的RAG查询优化
                search_query = f"健康管理计划 {question}"
                result = self.rag_tool.execute(search_query, top_k=5) # 增加检索数量
                return ("rag", result, self.rag_tool.format_context(result) if result.get("results") else "")
            except Exception as e:
                app_logger.warning(f"RAG检索失败: {e}")
                return ("rag", {"results": []}, "")

        def execute_kg_enrichment():
            """通过实体识别增强KG查询"""
            try:
                # 尝试从问题和用户画像中提取实体
                text_to_analyze = f"{question} {str(profile)}"
                entities = self.entity_recognizer.extract_entities(text_to_analyze)
                diseases = entities.get("diseases", [])
                
                kg_context_parts = []
                found_info = False
                
                for disease in diseases:
                    # 获取疾病详情，特别是包含饮食/运动建议的可能字段（如果有）
                    info = self.kg_tool.execute("get_disease_info", disease_name=disease)
                    if info.get("found"):
                        formatted = self.kg_tool.format_disease_info(info)
                        kg_context_parts.append(formatted)
                        found_info = True
                
                return ("kg", found_info, "\n\n".join(kg_context_parts))
            except Exception as e:
                app_logger.warning(f"KG增强查询失败: {e}")
                return ("kg", False, "")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(execute_rag): "rag",
                executor.submit(execute_kg_enrichment): "kg"
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
                        if result: # found_info is True
                            kg_context = formatted_context
                            tools_used.append("knowledge_graph_query")
                except Exception as e:
                    app_logger.warning(f"任务执行失败: {e}")
            
        # 2. 整合上下文
        history_text = self._format_history(context)
        
        combined_context = ""
        if rag_context:
            combined_context += f"【参考指南】\n{rag_context}\n"
        if kg_context:
            combined_context += f"\n【疾病知识】\n{kg_context}\n"
            
        full_context = f"{history_text}{combined_context}" if history_text else combined_context
        
        # 3. 生成计划
        prompt = PromptTemplate.format_health_plan_prompt(question, profile, full_context)
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        # 4. Fallback处理
        answer = self.format_answer_with_fallback(answer, full_context)
        
        return {
            "answer": answer,
            "plan_type": "health_management",
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": tools_used
        }
    
    def _handle_health_tracking(self, question: str, profile: Dict, context: Dict, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """处理健康数据追踪"""
        history_text = self._format_history(context)
        
        prompt = f"""{history_text}
用户健康数据追踪咨询：

用户问题：{question}
用户信息：{profile}

请提供健康数据追踪建议，包括：
1. 需要追踪的指标
2. 追踪频率
3. 数据记录方法
4. 异常情况处理"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "tools_used": []
        }
