"""运营分析类 Prompt - 数据分析 / 系统监控 / 报告生成

为运营 Agent 提供数据分析、系统监控、优化建议、报告生成的 Prompt 模板。
"""


class OperationsPrompts:
    """运营分析类 Prompt 集合"""

    # ================================================================
    # 系统 Prompt
    # ================================================================

    SYSTEM = """你是一位专业的运营分析AI。你的职责是：
1. 分析咨询数据和系统使用情况
2. 监控系统性能指标
3. 提供知识库优化建议
4. 生成运营报告
5. 识别系统改进机会"""

    # ================================================================
    # 用户 Prompt 模板
    # ================================================================

    DATA_ANALYSIS = """请分析以下运营数据：

{data}

请提供：
1. 关键指标总结
2. 趋势分析
3. 异常情况识别
4. 改进建议"""

    SYSTEM_MONITORING = """请分析以下系统监控指标：

{metrics}

请提供：
1. 系统健康状态评估
2. 性能指标分析
3. 潜在问题识别
4. 优化建议"""

    OPTIMIZATION = """基于以下上下文，提供知识库和系统优化建议：

{context}

请提供：
1. 知识库内容优化建议
2. 检索效果改进方案
3. Agent性能优化建议
4. 用户体验改进建议"""

    REPORT = """请生成运营报告：

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
    def format_data_analysis(data: str) -> str:
        return OperationsPrompts.DATA_ANALYSIS.format(data=data)

    @staticmethod
    def format_system_monitoring(metrics: str) -> str:
        return OperationsPrompts.SYSTEM_MONITORING.format(metrics=metrics)

    @staticmethod
    def format_optimization(context: str) -> str:
        return OperationsPrompts.OPTIMIZATION.format(context=context)

    @staticmethod
    def format_report(data: str) -> str:
        return OperationsPrompts.REPORT.format(data=data)
