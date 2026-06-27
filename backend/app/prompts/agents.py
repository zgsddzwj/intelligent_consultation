"""Agent 系统 Prompt - 客服 / 健康管家 / 运营 Agent

包含各 Agent 的系统 Prompt、用户 Prompt 模板及格式化方法。
补全了原先在 llm_service.PromptTemplate 中缺失的
CUSTOMER_SERVICE_SYSTEM、HEALTH_MANAGER_SYSTEM 等定义。
"""


class AgentPrompts:
    """各 Agent 的 Prompt 集合"""

    # ================================================================
    # 客服 Agent
    # ================================================================

    CUSTOMER_SERVICE_SYSTEM = """你是一位专业的客服助手。你的职责是：
1. 处理用户的常见问题和系统使用咨询
2. 提供清晰、耐心的指导
3. 收集和确认用户反馈
4. 对超出能力范围的问题，引导用户联系相关渠道
5. 保持友好、专业的服务态度

注意：对于医疗专业问题，请引导用户使用医疗咨询功能。"""

    CUSTOMER_SERVICE_USER = """基于以下信息，回答用户的问题：

{context}

用户问题：{question}

请提供清晰、友好的回答。"""

    CUSTOMER_FEEDBACK_USER = """{history}
用户反馈：

反馈内容：{question}
反馈数据：{feedback_data}

请确认收到反馈，并表示感谢。"""

    # ================================================================
    # 健康管家 Agent
    # ================================================================

    HEALTH_MANAGER_SYSTEM = """你是一位专业的健康管家AI。你的职责是：
1. 提供慢性病管理建议和生活方式指导
2. 基于医疗文献和知识图谱，制定个性化健康管理计划
3. 解答健康数据追踪相关问题
4. 所有建议必须标注信息来源
5. 对于不确定的信息，明确说明"暂无明确指南支持"
6. 在回答结尾添加免责声明："本回答仅供参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱"

注意：健康管理建议不能替代医生的诊疗方案。"""

    HEALTH_MANAGEMENT_USER = """基于以下健康管理信息，回答用户的问题：

{context}

用户问题：{question}

请提供专业、实用的健康管理建议。"""

    HEALTH_PLAN_USER = """{history}
请为以下用户制定健康管理计划：

用户问题：{question}
用户信息：{profile}

参考资料：
{context}

请提供包含以下内容的健康管理计划：
1. 健康目标设定
2. 生活方式建议（饮食、运动、睡眠）
3. 慢病管理要点
4. 监测指标和频率
5. 注意事项

请标注信息来源。"""

    HEALTH_TRACKING_USER = """{history}
用户健康数据追踪咨询：

用户问题：{question}
用户信息：{profile}

请提供健康数据追踪建议，包括：
1. 需要追踪的指标
2. 追踪频率
3. 数据记录方法
4. 异常情况处理"""

    # ================================================================
    # 运营 Agent
    # ================================================================

    OPERATIONS_SYSTEM = """你是一位专业的运营分析AI。你的职责是：
1. 分析咨询数据和系统使用情况
2. 监控系统性能指标
3. 提供知识库优化建议
4. 生成运营报告
5. 识别系统改进机会"""

    OPERATIONS_DATA_ANALYSIS = """请分析以下运营数据：

{data}

请提供：
1. 关键指标总结
2. 趋势分析
3. 异常情况识别
4. 改进建议"""

    OPERATIONS_SYSTEM_MONITORING = """请分析以下系统监控指标：

{metrics}

请提供：
1. 系统健康状态评估
2. 性能指标分析
3. 潜在问题识别
4. 优化建议"""

    OPERATIONS_OPTIMIZATION = """基于以下上下文，提供知识库和系统优化建议：

{context}

请提供：
1. 知识库内容优化建议
2. 检索效果改进方案
3. Agent性能优化建议
4. 用户体验改进建议"""

    OPERATIONS_REPORT = """请生成运营报告：

{data}

报告应包括：
1. 数据概览
2. 关键指标
3. 趋势分析
4. 问题与建议"""

    # ================================================================
    # 格式化方法
    # ================================================================

    @staticmethod
    def format_customer_service_prompt(question: str, context: str = "") -> str:
        """格式化客服咨询用户 Prompt"""
        return AgentPrompts.CUSTOMER_SERVICE_USER.format(
            context=context, question=question
        )

    @staticmethod
    def format_feedback_prompt(
        question: str, feedback_data: str, history: str = ""
    ) -> str:
        """格式化用户反馈 Prompt"""
        return AgentPrompts.CUSTOMER_FEEDBACK_USER.format(
            history=history, question=question, feedback_data=feedback_data
        )

    @staticmethod
    def format_health_management_prompt(question: str, context: str = "") -> str:
        """格式化健康管理咨询用户 Prompt"""
        return AgentPrompts.HEALTH_MANAGEMENT_USER.format(
            context=context, question=question
        )

    @staticmethod
    def format_health_plan_prompt(
        question: str, profile: str, context: str = "", history: str = ""
    ) -> str:
        """格式化健康计划用户 Prompt"""
        return AgentPrompts.HEALTH_PLAN_USER.format(
            history=history, question=question, profile=profile, context=context
        )

    @staticmethod
    def format_health_tracking_prompt(
        question: str, profile: str, history: str = ""
    ) -> str:
        """格式化健康追踪用户 Prompt"""
        return AgentPrompts.HEALTH_TRACKING_USER.format(
            history=history, question=question, profile=profile
        )

    @staticmethod
    def format_data_analysis_prompt(data: str) -> str:
        """格式化数据分析 Prompt"""
        return AgentPrompts.OPERATIONS_DATA_ANALYSIS.format(data=data)

    @staticmethod
    def format_system_monitoring_prompt(metrics: str) -> str:
        """格式化系统监控 Prompt"""
        return AgentPrompts.OPERATIONS_SYSTEM_MONITORING.format(metrics=metrics)

    @staticmethod
    def format_optimization_prompt(context: str) -> str:
        """格式化优化建议 Prompt"""
        return AgentPrompts.OPERATIONS_OPTIMIZATION.format(context=context)

    @staticmethod
    def format_report_prompt(data: str) -> str:
        """格式化运营报告 Prompt"""
        return AgentPrompts.OPERATIONS_REPORT.format(data=data)
