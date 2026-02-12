"""客服Agent"""
from typing import Dict, Any, Optional
import time
from app.agents.base import BaseAgent
from app.agents.tools.rag_tool import RAGTool
from app.services.llm_service import PromptTemplate
from app.utils.logger import app_logger


class CustomerServiceAgent(BaseAgent):
    """客服Agent - 处理常见问题、系统使用指导等"""
    
    def __init__(self):
        super().__init__(
            name="customer_service",
            description="客服助手，处理常见问题、系统使用指导、用户反馈"
        )
        
        # 添加工具
        self.rag_tool = RAGTool()
        self.add_tool(self.rag_tool)
        
        # FAQ数据（作为快速缓存）
        self.faq_data = {
            "如何使用系统": "您可以通过对话界面与AI医生进行咨询，也可以使用知识库搜索功能查找医疗信息。",
            "系统功能": "本系统提供医疗咨询、健康管理、知识库查询等功能。",
            "数据安全": "我们严格遵守数据保护法规，所有用户数据都经过加密处理。",
            "如何联系": "您可以通过系统内的反馈功能联系我们。"
        }
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return PromptTemplate.CUSTOMER_SERVICE_SYSTEM
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理客服咨询"""
        start_time = time.time()
        trace_id = input_data.get("trace_id")
        
        try:
            question = input_data.get("question", "")
            context = input_data.get("context", {})
            request_type = input_data.get("type", "faq")  # faq, guidance, feedback
            
            app_logger.info(f"客服Agent处理请求: {question[:50]}...")
            
            if request_type == "feedback":
                result = self._handle_feedback(question, input_data.get("feedback_data", {}), context)
            else:
                # 统一处理咨询类请求
                result = self._handle_inquiry(question, context, request_type)
            
            execution_time = time.time() - start_time
            tools_used = result.get("tools_used", [])
            self.log_execution(input_data, result, execution_time, tools_used)
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            app_logger.error(f"客服Agent处理失败: {e}")
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
    
    def _handle_inquiry(self, question: str, context: Dict, request_type: str = "faq") -> Dict[str, Any]:
        """处理咨询（FAQ或指导）"""
        tools_used = []
        
        # 1. 检查静态FAQ（仅对FAQ类型）
        if request_type == "faq":
            question_lower = question.lower()
            for key, answer in self.faq_data.items():
                if key in question_lower:
                    return {
                        "answer": answer,
                        "type": "faq",
                        "matched_key": key,
                        "tools_used": ["static_faq"]
                    }
        
        # 2. RAG检索（尝试查找系统文档）
        rag_context = ""
        try:
            # 搜索系统相关文档
            rag_result = self.rag_tool.execute(question, top_k=3)
            if rag_result.get("results"):
                rag_context = self.rag_tool.format_context(rag_result)
                tools_used.append("rag_search")
        except Exception:
            rag_result = {"results": []}
        
        # 3. 整合上下文
        history_text = self._format_history(context)
        full_context = f"{history_text}{rag_context}" if history_text else rag_context
        
        # 4. 生成回答
        prompt = PromptTemplate.format_customer_service_prompt(question, full_context)
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": request_type,
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": tools_used
        }
    
    def _handle_feedback(self, question: str, feedback_data: Dict, context: Dict) -> Dict[str, Any]:
        """处理用户反馈"""
        history_text = self._format_history(context)
        
        prompt = f"""{history_text}
用户反馈：

反馈内容：{question}
反馈数据：{feedback_data}

请确认收到反馈，并表示感谢。"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "feedback",
            "feedback_received": True,
            "tools_used": []
        }
