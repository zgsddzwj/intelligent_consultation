"""Agent编排器 - 基于LangGraph"""
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from app.agents.doctor_agent import DoctorAgent
from app.agents.health_manager_agent import HealthManagerAgent
from app.agents.customer_service_agent import CustomerServiceAgent
from app.agents.operations_agent import OperationsAgent
from app.utils.logger import app_logger
from app.config import get_settings
from app.knowledge.ml.intent_classifier import IntentClassifier

settings = get_settings()


class AgentState(TypedDict):
    """Agent状态"""
    messages: Annotated[list, add_messages]
    user_input: str
    intent: str
    agent_type: str
    result: Dict[str, Any]
    context: Dict[str, Any]


class AgentOrchestrator:
    """Agent编排器"""
    
    def __init__(self):
        self.doctor_agent = DoctorAgent()
        self.health_manager_agent = HealthManagerAgent()
        self.customer_service_agent = CustomerServiceAgent()
        self.operations_agent = OperationsAgent()
        
        # 初始化意图分类器（使用ML模型）
        self.intent_classifier = None
        if settings.ENABLE_INTENT_CLASSIFICATION:
            try:
                self.intent_classifier = IntentClassifier(model_dir=settings.INTENT_MODEL_DIR)
                app_logger.info("意图分类器初始化成功（ML模型）")
            except Exception as e:
                app_logger.warning(f"意图分类器初始化失败，将使用规则分类: {e}")
        
        # 构建工作流图
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("intent_classifier", self._classify_intent)
        workflow.add_node("doctor_agent", self._route_to_doctor)
        workflow.add_node("health_manager_agent", self._route_to_health_manager)
        workflow.add_node("customer_service_agent", self._route_to_customer_service)
        workflow.add_node("operations_agent", self._route_to_operations)
        workflow.add_node("risk_assessment", self._assess_risk)
        workflow.add_node("finalize", self._finalize_response)
        
        # 设置入口点
        workflow.set_entry_point("intent_classifier")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "intent_classifier",
            self._route_by_intent,
            {
                "doctor": "doctor_agent",
                "health_manager": "health_manager_agent",
                "customer_service": "customer_service_agent",
                "operations": "operations_agent"
            }
        )
        
        # 医生Agent后需要风险评估
        workflow.add_edge("doctor_agent", "risk_assessment")
        workflow.add_edge("health_manager_agent", "finalize")
        workflow.add_edge("customer_service_agent", "finalize")
        workflow.add_edge("operations_agent", "finalize")
        
        # 风险评估后到最终处理
        workflow.add_conditional_edges(
            "risk_assessment",
            self._route_by_risk,
            {
                "high_risk": "finalize",
                "normal": "finalize"
            }
        )
        
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _classify_intent(self, state: AgentState) -> AgentState:
        """意图分类（优先使用ML模型，回退到规则）"""
        user_input = state.get("user_input", "")
        
        # 优先使用ML模型分类
        if self.intent_classifier and self.intent_classifier.svm_model:
            try:
                result = self.intent_classifier.classify(user_input)
                ml_intent = result.get("intent", "")
                confidence = result.get("confidence", 0.0)
                
                # 将ML意图映射到Agent类型
                intent_mapping = {
                    "diagnosis": "doctor",
                    "medication": "doctor",
                    "examination": "doctor",
                    "symptom_inquiry": "doctor",
                    "disease_info": "doctor",
                    "health_management": "health_manager",
                    "general": "customer_service"
                }
                
                agent_type = intent_mapping.get(ml_intent, "customer_service")
                
                app_logger.info(
                    f"意图分类（ML）: {ml_intent} -> {agent_type}, "
                    f"置信度: {confidence:.2f}"
                )
                
                state["intent"] = ml_intent
                state["agent_type"] = agent_type
                state["context"]["intent_confidence"] = confidence
                return state
            except Exception as e:
                app_logger.warning(f"ML意图分类失败，使用规则分类: {e}")
        
        # 回退到规则分类
        intent_keywords = {
            "doctor": ["症状", "诊断", "疾病", "用药", "检查", "治疗", "病"],
            "health_manager": ["健康", "管理", "计划", "生活方式", "慢病", "追踪"],
            "customer_service": ["如何使用", "功能", "帮助", "问题", "反馈"],
            "operations": ["数据", "分析", "报告", "监控", "优化"]
        }
        
        user_lower = user_input.lower()
        intent_scores = {}
        
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in user_lower)
            intent_scores[intent] = score
        
        # 选择得分最高的意图
        intent = max(intent_scores, key=intent_scores.get) if intent_scores else "customer_service"
        
        app_logger.info(f"意图分类（规则）: {intent}")
        
        state["intent"] = intent
        state["agent_type"] = intent
        state["context"]["intent_confidence"] = 0.7  # 规则分类默认置信度
        return state
    
    def _route_by_intent(self, state: AgentState) -> str:
        """根据意图路由"""
        return state.get("intent", "customer_service")
    
    def _route_to_doctor(self, state: AgentState) -> AgentState:
        """路由到医生Agent"""
        user_input = state.get("user_input", "")
        context = state.get("context", {})
        
        # 判断咨询类型
        consultation_type = "general"
        if any(keyword in user_input for keyword in ["症状", "诊断", "可能"]):
            consultation_type = "diagnosis"
        elif any(keyword in user_input for keyword in ["用药", "药物", "药"]):
            consultation_type = "drug"
        
        input_data = {
            "question": user_input,
            "context": context,
            "type": consultation_type
        }
        
        result = self.doctor_agent.process(input_data)
        state["result"] = result
        return state
    
    def _route_to_health_manager(self, state: AgentState) -> AgentState:
        """路由到健康管家Agent"""
        user_input = state.get("user_input", "")
        context = state.get("context", {})
        
        request_type = "general"
        if any(keyword in user_input for keyword in ["计划", "制定"]):
            request_type = "plan"
        elif any(keyword in user_input for keyword in ["追踪", "记录", "数据"]):
            request_type = "tracking"
        
        input_data = {
            "question": user_input,
            "context": context,
            "type": request_type,
            "user_profile": context.get("user_profile", {})
        }
        
        result = self.health_manager_agent.process(input_data)
        state["result"] = result
        return state
    
    def _route_to_customer_service(self, state: AgentState) -> AgentState:
        """路由到客服Agent"""
        user_input = state.get("user_input", "")
        
        request_type = "faq"
        if any(keyword in user_input for keyword in ["指导", "如何", "怎么"]):
            request_type = "guidance"
        elif any(keyword in user_input for keyword in ["反馈", "建议", "意见"]):
            request_type = "feedback"
        
        input_data = {
            "question": user_input,
            "type": request_type
        }
        
        result = self.customer_service_agent.process(input_data)
        state["result"] = result
        return state
    
    def _route_to_operations(self, state: AgentState) -> AgentState:
        """路由到运营Agent"""
        context = state.get("context", {})
        
        request_type = context.get("request_type", "analysis")
        
        input_data = {
            "type": request_type,
            "data": context.get("data", {}),
            "metrics": context.get("metrics", {})
        }
        
        result = self.operations_agent.process(input_data)
        state["result"] = result
        return state
    
    def _assess_risk(self, state: AgentState) -> AgentState:
        """风险评估"""
        result = state.get("result", {})
        risk_level = result.get("risk_level", "low")
        
        state["context"] = state.get("context", {})
        state["context"]["risk_level"] = risk_level
        
        # 如果是高风险，添加额外提示
        if risk_level in ["high", "critical"]:
            result["answer"] = result.get("answer", "") + "\n\n⚠️ 重要提示：建议立即就医或拨打急救电话。"
        
        state["result"] = result
        return state
    
    def _route_by_risk(self, state: AgentState) -> str:
        """根据风险等级路由"""
        risk_level = state.get("context", {}).get("risk_level", "low")
        return "high_risk" if risk_level in ["high", "critical"] else "normal"
    
    def _finalize_response(self, state: AgentState) -> AgentState:
        """最终处理响应"""
        result = state.get("result", {})
        
        # 添加运营记录（异步）
        try:
            self.operations_agent.process({
                "type": "analysis",
                "data": {
                    "agent_type": state.get("agent_type"),
                    "user_input": state.get("user_input"),
                    "timestamp": state.get("context", {}).get("timestamp")
                }
            })
        except Exception as e:
            app_logger.warning(f"运营记录失败: {e}")
        
        return state
    
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户输入"""
        try:
            initial_state = {
                "messages": [],
                "user_input": user_input,
                "intent": "",
                "agent_type": "",
                "result": {},
                "context": context or {}
            }
            
            # 执行工作流
            final_state = self.workflow.invoke(initial_state)
            
            return final_state.get("result", {})
            
        except Exception as e:
            app_logger.error(f"编排器处理失败: {e}")
            return {
                "answer": "处理请求时发生错误，请稍后重试。",
                "error": str(e)
            }

