"""Agent编排器 - 极致优化版（状态缓存、并行路由、执行统计、工作流可视化）"""
import asyncio
import time
import threading
from typing import Dict, Any, TypedDict, Annotated, Optional, List
from functools import lru_cache
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.agents.doctor_agent import DoctorAgent
from app.agents.health_manager_agent import HealthManagerAgent
from app.agents.customer_service_agent import CustomerServiceAgent
from app.agents.operations_agent import OperationsAgent
from app.utils.logger import app_logger
from app.config import get_settings
from app.knowledge.ml.intent_classifier import IntentClassifier
from app.services.langfuse_service import langfuse_service
from app.infrastructure.monitoring import track_consultation

settings = get_settings()


class AgentState(TypedDict):
    """Agent状态 - 增强版"""
    messages: Annotated[list, add_messages]
    user_input: str
    intent: str
    agent_type: str
    result: Dict[str, Any]
    context: Dict[str, Any]
    trace_id: Optional[str]
    execution_stats: Dict[str, Any]
    risk_level: str
    parallel_results: Optional[Dict[str, Any]]


class OrchestratorMetrics:
    """编排器性能指标收集器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._stats = {
            "total_requests": 0,
            "total_errors": 0,
            "avg_execution_time": 0.0,
            "intent_distribution": {},
            "agent_execution_times": {},
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def record_request(self, intent: str, execution_time: float, success: bool = True):
        with self._lock:
            self._stats["total_requests"] += 1
            if not success:
                self._stats["total_errors"] += 1
            n = self._stats["total_requests"]
            self._stats["avg_execution_time"] = (
                (self._stats["avg_execution_time"] * (n - 1) + execution_time) / n
            )
            self._stats["intent_distribution"][intent] = (
                self._stats["intent_distribution"].get(intent, 0) + 1
            )

    def record_agent_time(self, agent_type: str, duration: float):
        with self._lock:
            if agent_type not in self._stats["agent_execution_times"]:
                self._stats["agent_execution_times"][agent_type] = []
            times = self._stats["agent_execution_times"][agent_type]
            times.append(duration)
            self._stats["agent_execution_times"][agent_type] = times[-100:]

    def record_cache(self, hit: bool):
        with self._lock:
            if hit:
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = self._stats.copy()
            stats["agent_avg_times"] = {
                agent: sum(times) / len(times) if times else 0
                for agent, times in stats["agent_execution_times"].items()
            }
            total_cache = stats["cache_hits"] + stats["cache_misses"]
            stats["cache_hit_rate"] = (
                stats["cache_hits"] / total_cache * 100 if total_cache > 0 else 0
            )
            return stats


orchestrator_metrics = OrchestratorMetrics()


class AgentOrchestrator:
    """Agent编排器 - 极致优化版"""

    INTENT_KEYWORDS = {
        "doctor": ["症状", "诊断", "疾病", "用药", "检查", "治疗", "病", "疼", "痛", "不舒服"],
        "health_manager": ["健康", "管理", "计划", "生活方式", "慢病", "追踪", "运动", "饮食"],
        "customer_service": ["如何使用", "功能", "帮助", "问题", "反馈", "客服", "联系"],
        "operations": ["数据", "分析", "报告", "监控", "优化", "统计", "运营"]
    }

    INTENT_MAPPING = {
        "diagnosis": "doctor",
        "medication": "doctor",
        "examination": "doctor",
        "symptom_inquiry": "doctor",
        "disease_info": "doctor",
        "health_management": "health_manager",
        "general": "customer_service"
    }

    def __init__(self):
        self.doctor_agent = DoctorAgent()
        self.health_manager_agent = HealthManagerAgent()
        self.customer_service_agent = CustomerServiceAgent()
        self.operations_agent = OperationsAgent()

        self.intent_classifier = None
        if settings.ENABLE_INTENT_CLASSIFICATION:
            try:
                self.intent_classifier = IntentClassifier(model_dir=settings.INTENT_MODEL_DIR)
                app_logger.info("意图分类器初始化成功（ML模型）")
            except Exception as e:
                app_logger.warning(f"意图分类器初始化失败，将使用规则分类: {e}")

        self.workflow = self._build_workflow()

        self._state_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 30

    def _get_cached_state(self, user_input: str, context_hash: str) -> Optional[AgentState]:
        cache_key = f"{user_input}:{context_hash}"
        with self._cache_lock:
            cached = self._state_cache.get(cache_key)
            if cached and (time.time() - cached["timestamp"] < self._cache_ttl):
                orchestrator_metrics.record_cache(True)
                return cached["state"]
            self._state_cache = {
                k: v for k, v in self._state_cache.items()
                if time.time() - v["timestamp"] < self._cache_ttl
            }
        orchestrator_metrics.record_cache(False)
        return None

    def _set_cached_state(self, user_input: str, context_hash: str, state: AgentState):
        cache_key = f"{user_input}:{context_hash}"
        with self._cache_lock:
            self._state_cache[cache_key] = {
                "state": state,
                "timestamp": time.time()
            }

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("intent_classifier", self._classify_intent)
        workflow.add_node("doctor_agent", self._route_to_doctor)
        workflow.add_node("health_manager_agent", self._route_to_health_manager)
        workflow.add_node("customer_service_agent", self._route_to_customer_service)
        workflow.add_node("operations_agent", self._route_to_operations)
        workflow.add_node("risk_assessment", self._assess_risk)
        workflow.add_node("finalize", self._finalize_response)

        workflow.set_entry_point("intent_classifier")

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

        workflow.add_edge("doctor_agent", "risk_assessment")
        workflow.add_edge("health_manager_agent", "finalize")
        workflow.add_edge("customer_service_agent", "finalize")
        workflow.add_edge("operations_agent", "finalize")

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
        user_input = state.get("user_input", "")
        trace_id = state.get("trace_id")

        span = None
        if langfuse_service.enabled:
            span = langfuse_service.span(
                name="orchestrator.intent_classification",
                trace_id=trace_id,
                metadata={"user_input": user_input[:200]}
            )

        start_time = time.time()

        try:
            if self.intent_classifier and getattr(self.intent_classifier, 'svm_model', None):
                try:
                    result = self.intent_classifier.classify(user_input)
                    ml_intent = result.get("intent", "")
                    confidence = result.get("confidence", 0.0)

                    agent_type = self.INTENT_MAPPING.get(ml_intent, "customer_service")

                    app_logger.info(
                        f"意图分类（ML）: {ml_intent} -> {agent_type}, "
                        f"置信度: {confidence:.2f}"
                    )

                    state["intent"] = ml_intent
                    state["agent_type"] = agent_type
                    state["context"]["intent_confidence"] = confidence
                    state["context"]["classification_method"] = "ml"

                    if langfuse_service.enabled and span:
                        try:
                            span.end(metadata={
                                "intent": ml_intent,
                                "agent_type": agent_type,
                                "confidence": confidence,
                                "method": "ml",
                                "execution_time": time.time() - start_time
                            })
                        except Exception:
                            pass

                    return state
                except Exception as e:
                    app_logger.warning(f"ML意图分类失败，使用规则分类: {e}")
        except Exception as e:
            app_logger.warning(f"意图分类异常: {e}")

        user_lower = user_input.lower()
        intent_scores = {}

        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in user_lower)
            intent_scores[intent] = score

        intent = max(intent_scores, key=intent_scores.get) if any(intent_scores.values()) else "customer_service"

        app_logger.info(f"意图分类（规则）: {intent}")

        state["intent"] = intent
        state["agent_type"] = intent
        state["context"]["intent_confidence"] = 0.7
        state["context"]["classification_method"] = "rule"

        if langfuse_service.enabled and span:
            try:
                span.end(metadata={
                    "intent": intent,
                    "agent_type": intent,
                    "confidence": 0.7,
                    "method": "rule",
                    "execution_time": time.time() - start_time
                })
            except Exception:
                pass

        return state

    def _route_by_intent(self, state: AgentState) -> str:
        return state.get("agent_type", "customer_service")

    def _route_to_doctor(self, state: AgentState) -> AgentState:
        user_input = state.get("user_input", "")
        context = state.get("context", {})
        trace_id = state.get("trace_id")

        span = None
        if langfuse_service.enabled:
            span = langfuse_service.span(
                name="orchestrator.doctor_agent",
                trace_id=trace_id,
                metadata={"agent": "doctor", "user_input": user_input[:200]}
            )

        start_time = time.time()

        try:
            consultation_type = "general"
            if any(kw in user_input for kw in ["症状", "诊断", "可能", "疼", "痛"]):
                consultation_type = "diagnosis"
            elif any(kw in user_input for kw in ["用药", "药物", "药", "处方"]):
                consultation_type = "drug"
            elif any(kw in user_input for kw in ["检查", "化验", "影像", "CT", "MRI"]):
                consultation_type = "examination"

            input_data = {
                "question": user_input,
                "context": context,
                "type": consultation_type,
                "trace_id": trace_id
            }

            result = self.doctor_agent.process(input_data)
            state["result"] = result

            duration = time.time() - start_time
            orchestrator_metrics.record_agent_time("doctor", duration)

            if langfuse_service.enabled and span:
                try:
                    span.end(metadata={
                        "consultation_type": consultation_type,
                        "execution_time": duration,
                        "tools_used": result.get("tools_used", [])
                    })
                except Exception:
                    pass

            return state
        except Exception as e:
            duration = time.time() - start_time
            orchestrator_metrics.record_agent_time("doctor", duration)
            if langfuse_service.enabled and span:
                try:
                    span.end(metadata={
                        "error": True,
                        "error_message": str(e),
                        "execution_time": duration
                    })
                except Exception:
                    pass
            raise

    def _route_to_health_manager(self, state: AgentState) -> AgentState:
        user_input = state.get("user_input", "")
        context = state.get("context", {})

        start_time = time.time()

        request_type = "general"
        if any(kw in user_input for kw in ["计划", "制定", "方案"]):
            request_type = "plan"
        elif any(kw in user_input for kw in ["追踪", "记录", "数据", "监测"]):
            request_type = "tracking"
        elif any(kw in user_input for kw in ["饮食", "营养", "食谱"]):
            request_type = "diet"
        elif any(kw in user_input for kw in ["运动", "锻炼", "健身"]):
            request_type = "exercise"

        input_data = {
            "question": user_input,
            "context": context,
            "type": request_type,
            "user_profile": context.get("user_profile", {})
        }

        result = self.health_manager_agent.process(input_data)
        state["result"] = result

        duration = time.time() - start_time
        orchestrator_metrics.record_agent_time("health_manager", duration)

        return state

    def _route_to_customer_service(self, state: AgentState) -> AgentState:
        user_input = state.get("user_input", "")

        start_time = time.time()

        request_type = "faq"
        if any(kw in user_input for kw in ["指导", "如何", "怎么", "教程"]):
            request_type = "guidance"
        elif any(kw in user_input for kw in ["反馈", "建议", "意见", "投诉"]):
            request_type = "feedback"
        elif any(kw in user_input for kw in ["账号", "登录", "密码", "注册"]):
            request_type = "account"

        input_data = {
            "question": user_input,
            "type": request_type
        }

        result = self.customer_service_agent.process(input_data)
        state["result"] = result

        duration = time.time() - start_time
        orchestrator_metrics.record_agent_time("customer_service", duration)

        return state

    def _route_to_operations(self, state: AgentState) -> AgentState:
        context = state.get("context", {})

        start_time = time.time()

        request_type = context.get("request_type", "analysis")

        input_data = {
            "type": request_type,
            "data": context.get("data", {}),
            "metrics": context.get("metrics", {}),
            "time_range": context.get("time_range", "7d")
        }

        result = self.operations_agent.process(input_data)
        state["result"] = result

        duration = time.time() - start_time
        orchestrator_metrics.record_agent_time("operations", duration)

        return state

    def _assess_risk(self, state: AgentState) -> AgentState:
        result = state.get("result", {})
        context = state.get("context", {})

        risk_signals = []
        answer = result.get("answer", "")

        high_risk_keywords = ["紧急", "立即", "危险", "严重", "致命", "抢救", "急救"]
        medium_risk_keywords = ["注意", "建议", "尽快", "复查", "随访"]

        risk_score = 0
        for keyword in high_risk_keywords:
            if keyword in answer:
                risk_score += 3
                risk_signals.append(keyword)

        for keyword in medium_risk_keywords:
            if keyword in answer:
                risk_score += 1
                risk_signals.append(keyword)

        if risk_score >= 3:
            risk_level = "high"
        elif risk_score >= 1:
            risk_level = "medium"
        else:
            risk_level = "low"

        context["risk_level"] = risk_level
        context["risk_score"] = risk_score
        context["risk_signals"] = risk_signals
        state["context"] = context
        state["risk_level"] = risk_level

        if risk_level == "high":
            result["risk_warning"] = {
                "level": "high",
                "message": "⚠️ 检测到高风险内容，建议立即就医或联系急救服务。",
                "signals": risk_signals
            }
            state["result"] = result

        return state

    def _route_by_risk(self, state: AgentState) -> str:
        risk_level = state.get("risk_level", "low")
        return "high_risk" if risk_level in ["high", "critical"] else "normal"

    def _finalize_response(self, state: AgentState) -> AgentState:
        result = state.get("result", {})
        context = state.get("context", {})

        result["metadata"] = {
            "agent_type": state.get("agent_type"),
            "intent": state.get("intent"),
            "intent_confidence": context.get("intent_confidence"),
            "classification_method": context.get("classification_method"),
            "risk_level": state.get("risk_level", "low"),
            "risk_score": context.get("risk_score", 0),
            "timestamp": time.time(),
        }

        try:
            def _log_operations():
                try:
                    self.operations_agent.process({
                        "type": "analysis",
                        "data": {
                            "agent_type": state.get("agent_type"),
                            "user_input": state.get("user_input", "")[:500],
                            "intent": state.get("intent"),
                            "timestamp": time.time()
                        }
                    })
                except Exception:
                    pass

            threading.Thread(target=_log_operations, daemon=True).start()
        except Exception as e:
            app_logger.warning(f"运营记录失败: {e}")

        state["result"] = result
        return state

    def process(self, user_input: str, context: Dict[str, Any] = None,
                user_id: Optional[str] = None,
                session_id: Optional[str] = None,
                trace_id: Optional[str] = None) -> Dict[str, Any]:
        context = context or {}

        context_hash = str(hash(str(sorted(context.items()))))[:8]

        cached = self._get_cached_state(user_input, context_hash)
        if cached:
            app_logger.info("编排器状态缓存命中")
            return cached.get("result", {})

        trace = None
        if langfuse_service.enabled and not trace_id:
            trace = langfuse_service.trace(
                name="agent_orchestrator.process",
                user_id=user_id,
                session_id=session_id,
                metadata={
                    "user_input": user_input[:200],
                    "context_keys": list(context.keys())
                }
            )
            trace_id = trace.id if trace and hasattr(trace, 'id') else None

        start_time = time.time()
        success = True

        try:
            initial_state = {
                "messages": [],
                "user_input": user_input,
                "intent": "",
                "agent_type": "",
                "result": {},
                "context": context,
                "trace_id": trace_id,
                "execution_stats": {},
                "risk_level": "low",
                "parallel_results": {}
            }

            final_state = self.workflow.invoke(initial_state)

            result = final_state.get("result", {})
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            result["trace_id"] = trace_id

            intent = final_state.get("intent", "unknown")
            orchestrator_metrics.record_request(intent, execution_time, success=True)
            track_consultation(final_state.get("agent_type", "unknown"), "success", execution_time)

            self._set_cached_state(user_input, context_hash, final_state)

            return result

        except Exception as e:
            success = False
            execution_time = time.time() - start_time
            orchestrator_metrics.record_request("error", execution_time, success=False)
            track_consultation("unknown", "error", execution_time)

            app_logger.error(f"编排器处理失败: {e}")

            if langfuse_service.enabled and trace:
                try:
                    langfuse_service.span(
                        name="orchestrator.error",
                        trace_id=trace_id,
                        metadata={
                            "error": True,
                            "error_message": str(e),
                            "execution_time": execution_time
                        }
                    )
                except Exception:
                    pass

            return {
                "answer": "处理请求时发生错误，请稍后重试。",
                "error": str(e),
                "trace_id": trace_id,
                "metadata": {
                    "error": True,
                    "execution_time": execution_time
                }
            }

    def get_metrics(self) -> Dict[str, Any]:
        return orchestrator_metrics.get_stats()

    def get_workflow_graph(self) -> Dict[str, Any]:
        """获取工作流图结构（用于可视化）"""
        return {
            "nodes": [
                {"id": "intent_classifier", "type": "classifier", "label": "意图分类"},
                {"id": "doctor_agent", "type": "agent", "label": "医生Agent"},
                {"id": "health_manager_agent", "type": "agent", "label": "健康管家"},
                {"id": "customer_service_agent", "type": "agent", "label": "客服Agent"},
                {"id": "operations_agent", "type": "agent", "label": "运营Agent"},
                {"id": "risk_assessment", "type": "assessment", "label": "风险评估"},
                {"id": "finalize", "type": "output", "label": "最终输出"},
            ],
            "edges": [
                {"from": "intent_classifier", "to": "doctor_agent", "condition": "doctor"},
                {"from": "intent_classifier", "to": "health_manager_agent", "condition": "health_manager"},
                {"from": "intent_classifier", "to": "customer_service_agent", "condition": "customer_service"},
                {"from": "intent_classifier", "to": "operations_agent", "condition": "operations"},
                {"from": "doctor_agent", "to": "risk_assessment"},
                {"from": "health_manager_agent", "to": "finalize"},
                {"from": "customer_service_agent", "to": "finalize"},
                {"from": "operations_agent", "to": "finalize"},
                {"from": "risk_assessment", "to": "finalize"},
            ],
            "entry_point": "intent_classifier",
            "end_point": "finalize"
        }
