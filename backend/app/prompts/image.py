"""图片分析类 Prompt - 图片分类 / 多模态诊断 / 描述生成

用于医疗图片理解、结构化诊断报告生成、表格/图片描述等场景。
"""
from typing import Optional


class ImagePrompts:
    """图片分析类 Prompt 集合"""

    # ================================================================
    # 图片内容理解（默认查询）
    # ================================================================

    IMAGE_UNDERSTAND_DEFAULT = "请描述这张图片中的医疗相关内容"

    IMAGE_MEDICAL_TERMS = (
        "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，"
        "并以列表形式返回。"
    )

    IMAGE_ANALYZE_DEFAULT = (
        "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并提取出来。"
    )

    # ================================================================
    # 图片类型分类
    # ================================================================

    IMAGE_CLASSIFY = (
        "请判断这张图片属于以下哪种医疗图片类型，只返回类型名称（不要其他文字）：\n"
        "- lab_report: 化验报告/检验单（血常规、尿常规、生化等）\n"
        "- prescription: 处方/用药单\n"
        "- skin_condition: 皮肤病灶/皮疹照片\n"
        "- xray: X光片\n"
        "- ct_scan: CT/MRI影像\n"
        "- ultrasound: 超声/B超图像\n"
        "- ecg: 心电图\n"
        "- medical_record: 病历记录\n"
        "- other: 非医疗图片"
    )

    # ================================================================
    # 多模态诊断报告生成
    # ================================================================

    DIAGNOSIS_REPORT_TEMPLATE = """你是一位专业的医疗影像分析AI。请仔细分析这张医疗相关图片，并生成结构化诊断报告。
{context_section}
请按以下JSON格式返回结果（只返回JSON，不要其他文字）：
{{
    "image_type": "图片类型（lab_report|prescription|skin_condition|xray|ct_scan|other）",
    "image_type_confidence": 0.0-1.0的置信度,
    "findings": [
        {{
            "category": "发现类别（如：异常指标、阳性发现、阴性发现）",
            "item": "具体项目名称",
            "value": "检测值或描述",
            "reference": "参考范围（如适用）",
            "abnormality": "normal|abnormal_low|abnormal_high|positive|negative"
        }}
    ],
    "summary": "诊断摘要（简洁描述图片中的关键发现）",
    "recommendations": [
        "建议1",
        "建议2"
    ],
    "risk_level": "low|medium|high"
}}

注意：
1. 如果图片不是医疗相关内容，image_type 设为 "other"，findings 为空数组
2. risk_level 基于发现的异常程度判断
3. recommendations 应包含后续检查或就诊建议
4. 只返回JSON，不要添加Markdown格式或其他说明"""

    # image_processor.py 中使用的简化版结构化报告
    IMAGE_PROCESSOR_REPORT_TEMPLATE = """请分析这张医疗图片并生成结构化诊断报告。{context_section}

请以JSON格式返回（只返回JSON）：
{{
    "findings": [
        {{"category": "发现类别", "item": "项目", "value": "值", "reference": "参考范围", "abnormality": "normal|abnormal_low|abnormal_high|positive|negative"}}
    ],
    "summary": "诊断摘要",
    "recommendations": ["建议1", "建议2"],
    "risk_level": "low|medium|high"
}}"""

    # ================================================================
    # 表格描述生成
    # ================================================================

    TABLE_DESCRIPTION_SYSTEM = "你是一个专业的数据分析师，擅长分析表格数据并生成准确、简洁的描述。"

    TABLE_DESCRIPTION_USER = """{context_section}{title_section}表格HTML：
{table_html}

请分析这个表格，生成简洁的文字描述，包括表格的主要内容和关键数据。"""

    # ================================================================
    # 图片描述生成
    # ================================================================

    IMAGE_DESCRIPTION_SYSTEM = "你是一个专业的医疗图像分析师，擅长识别和分析医疗相关的图表、数据可视化等信息。"

    IMAGE_DESCRIPTION_USER = """{context_before_section}{title_section}请详细描述这张图片中的医疗相关内容，包括图表、文字、数据等信息。{context_after_section}"""

    # ================================================================
    # 格式化方法
    # ================================================================

    @staticmethod
    def format_diagnosis_report_prompt(patient_context: str = "") -> str:
        """格式化多模态诊断报告 Prompt（API 层使用）"""
        context_section = (
            f"\n患者背景信息：{patient_context}\n" if patient_context else ""
        )
        return ImagePrompts.DIAGNOSIS_REPORT_TEMPLATE.format(
            context_section=context_section
        )

    @staticmethod
    def format_image_processor_report_prompt(patient_context: str = "") -> str:
        """格式化 image_processor 结构化报告 Prompt"""
        context_section = (
            f"\n患者背景：{patient_context}\n" if patient_context else ""
        )
        return ImagePrompts.IMAGE_PROCESSOR_REPORT_TEMPLATE.format(
            context_section=context_section
        )

    @staticmethod
    def format_table_description_prompt(
        table_html: str,
        table_title: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """格式化表格描述 Prompt"""
        context_section = f"上下文信息：\n{context}\n\n" if context else ""
        title_section = f"表格标题：{table_title}\n\n" if table_title else ""
        return ImagePrompts.TABLE_DESCRIPTION_USER.format(
            context_section=context_section,
            title_section=title_section,
            table_html=table_html,
        )

    @staticmethod
    def format_image_description_prompt(
        image_title: Optional[str] = None,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
    ) -> str:
        """格式化图片描述 Prompt"""
        context_before_section = (
            f"前文上下文：\n{context_before}\n\n" if context_before else ""
        )
        title_section = f"图片标题：{image_title}\n\n" if image_title else ""
        context_after_section = (
            f"\n\n后文上下文：\n{context_after}" if context_after else ""
        )
        return ImagePrompts.IMAGE_DESCRIPTION_USER.format(
            context_before_section=context_before_section,
            title_section=title_section,
            context_after_section=context_after_section,
        )
