"""客服Agent"""
from typing import Dict, Any
import time
from app.agents.base import BaseAgent
from app.utils.logger import app_logger


class CustomerServiceAgent(BaseAgent):
    """客服Agent - 处理常见问题、系统使用指导等"""
    
    def __init__(self):
        super().__init__(
            name="customer_service",
            description="客服助手，处理常见问题、系统使用指导、用户反馈"
        )
        
        # FAQ数据（可以存储在数据库中）
        self.faq_data = {
            "如何使用系统": "您可以通过对话界面与AI医生进行咨询，也可以使用知识库搜索功能查找医疗信息。",
            "系统功能": "本系统提供医疗咨询、健康管理、知识库查询等功能。",
            "数据安全": "我们严格遵守数据保护法规，所有用户数据都经过加密处理。",
            "如何联系": "您可以通过系统内的反馈功能联系我们。"
        }
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return """你是一位专业的客服助手。你的职责是：
1. 回答用户关于系统使用的常见问题
2. 提供系统功能说明和操作指导
3. 处理用户反馈和建议
4. 帮助用户解决使用中的问题
5. 保持友好、耐心的服务态度"""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理客服咨询"""
        start_time = time.time()
        
        try:
            question = input_data.get("question", "")
            request_type = input_data.get("type", "faq")  # faq, guidance, feedback
            
            app_logger.info(f"客服Agent处理请求: {question[:50]}...")
            
            if request_type == "faq":
                result = self._handle_faq(question)
            elif request_type == "guidance":
                result = self._handle_guidance(question)
            elif request_type == "feedback":
                result = self._handle_feedback(question, input_data.get("feedback_data", {}))
            else:
                result = self._handle_general_inquiry(question)
            
            execution_time = time.time() - start_time
            self.log_execution(input_data, result, execution_time, [])
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            app_logger.error(f"客服Agent处理失败: {e}")
            execution_time = time.time() - start_time
            return {
                "answer": f"处理请求时发生错误: {str(e)}",
                "error": str(e),
                "execution_time": execution_time
            }
    
    def _handle_faq(self, question: str) -> Dict[str, Any]:
        """处理FAQ"""
        # 简单的关键词匹配
        question_lower = question.lower()
        for key, answer in self.faq_data.items():
            if key in question_lower:
                return {
                    "answer": answer,
                    "type": "faq",
                    "matched_key": key
                }
        
        # 如果没有匹配，使用LLM生成回答
        prompt = f"""用户问题：{question}

请基于以下常见问题信息，提供友好的回答：

{self.faq_data}

如果问题不在常见问题中，请提供一般性的帮助信息。"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "faq"
        }
    
    def _handle_guidance(self, question: str) -> Dict[str, Any]:
        """处理使用指导"""
        prompt = f"""用户需要系统使用指导：

问题：{question}

请提供详细的操作步骤和说明。"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "guidance"
        }
    
    def _handle_feedback(self, question: str, feedback_data: Dict) -> Dict[str, Any]:
        """处理用户反馈"""
        prompt = f"""用户反馈：

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
            "feedback_received": True
        }
    
    def _handle_general_inquiry(self, question: str) -> Dict[str, Any]:
        """处理一般咨询"""
        prompt = f"""用户咨询：{question}

请提供友好的帮助。"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "type": "general"
        }

