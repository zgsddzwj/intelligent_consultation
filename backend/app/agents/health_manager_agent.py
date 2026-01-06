"""健康管家Agent"""
from typing import Dict, Any
import time
from app.agents.base import BaseAgent
from app.agents.tools.rag_tool import RAGTool
from app.utils.logger import app_logger


class HealthManagerAgent(BaseAgent):
    """健康管家Agent - 提供慢病管理、健康计划等服务"""
    
    def __init__(self):
        super().__init__(
            name="health_manager",
            description="健康管家，提供慢病管理计划、生活方式建议、健康数据追踪"
        )
        
        self.rag_tool = RAGTool()
        self.add_tool(self.rag_tool)
    
    def get_system_prompt(self) -> str:
        """获取系统Prompt"""
        return """你是一位专业的健康管家。你的职责是：
1. 为用户制定个性化的健康管理计划
2. 提供生活方式建议（饮食、运动、作息等）
3. 帮助用户追踪和管理健康数据
4. 提供慢病管理指导
5. 鼓励用户保持健康的生活习惯"""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康管理咨询"""
        start_time = time.time()
        
        try:
            question = input_data.get("question", "")
            user_profile = input_data.get("user_profile", {})
            request_type = input_data.get("type", "general")  # general, plan, tracking
            
            app_logger.info(f"健康管家Agent处理请求: {question[:50]}...")
            
            if request_type == "plan":
                result = self._create_health_plan(question, user_profile)
            elif request_type == "tracking":
                result = self._handle_health_tracking(question, user_profile)
            else:
                result = self._handle_general_health_consultation(question, user_profile)
            
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
                "execution_time": execution_time
            }
    
    def _handle_general_health_consultation(self, question: str, profile: Dict) -> Dict[str, Any]:
        """处理一般健康咨询"""
        # RAG检索健康管理相关文档
        rag_result = self.rag_tool.execute(question, top_k=3)
        rag_context = self.rag_tool.format_context(rag_result)
        
        # 生成回答
        prompt = f"""基于以下健康管理信息，回答用户的问题：

{rag_context}

用户问题：{question}

请提供专业、实用的健康管理建议。"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": ["rag_search"]
        }
    
    def _create_health_plan(self, question: str, profile: Dict) -> Dict[str, Any]:
        """创建健康计划"""
        # 检索相关健康计划模板
        rag_result = self.rag_tool.execute("健康管理计划", top_k=3)
        rag_context = self.rag_tool.format_context(rag_result)
        
        prompt = f"""基于以下信息，为用户制定个性化的健康管理计划：

{rag_context}

用户需求：{question}
用户信息：{profile}

请制定详细的健康管理计划，包括：
1. 饮食建议
2. 运动计划
3. 作息安排
4. 健康监测指标
5. 注意事项"""
        
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7
        )
        
        return {
            "answer": answer,
            "plan_type": "health_management",
            "sources": [r.get("source") for r in rag_result.get("results", [])],
            "tools_used": ["rag_search"]
        }
    
    def _handle_health_tracking(self, question: str, profile: Dict) -> Dict[str, Any]:
        """处理健康数据追踪"""
        prompt = f"""用户健康数据追踪咨询：

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

