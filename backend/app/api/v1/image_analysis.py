"""图片分析API - 增强版（多模态诊断、结构化报告、图像分类）"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger
from app.utils.validators import validate_image_file
from app.config import get_settings
from app.infrastructure.retry import retry
from app.common.exceptions import LLMServiceException, ErrorCode
from app.prompts import ImagePrompts, KnowledgePrompts
import base64
import json
import re
import time

settings = get_settings()

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ImageAnalysisRequest(BaseModel):
    """图片分析请求"""
    image_base64: str
    prompt: Optional[str] = Field(
        default=ImagePrompts.IMAGE_ANALYZE_DEFAULT,
        description="分析提示词"
    )


class ImageAnalysisResponse(BaseModel):
    """图片分析响应"""
    medical_terms: List[Dict[str, str]]  # [{"term": "高血压", "type": "疾病"}, ...]
    extracted_text: str
    analysis_result: str


class MultimodalDiagnosisResponse(BaseModel):
    """多模态诊断响应"""
    image_type: str  # lab_report | prescription | skin_condition | xray | other
    image_type_confidence: float
    findings: List[Dict[str, Any]]  # 结构化发现
    summary: str
    recommendations: List[str]
    risk_level: str  # low | medium | high
    kg_references: List[Dict[str, Any]]  # 知识图谱关联信息


# ==================== 工具函数 ====================

def _parse_medical_terms_json(extraction_result: str) -> List[Dict[str, str]]:
    """
    从LLM提取结果中解析医疗术语JSON（多策略 fallback）
    """
    if not extraction_result:
        return []

    text = extraction_result.strip()

    # 策略1: 直接解析JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "terms" in data:
            terms = data["terms"]
            if isinstance(terms, list):
                return [t for t in terms if isinstance(t, dict) and "term" in t]
    except (json.JSONDecodeError, TypeError):
        pass

    # 策略2: 从Markdown代码块中提取JSON
    code_block_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]
    for pattern in code_block_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                if isinstance(data, dict) and "terms" in data:
                    terms = data["terms"]
                    if isinstance(terms, list):
                        return [t for t in terms if isinstance(t, dict) and "term" in t]
            except (json.JSONDecodeError, TypeError):
                continue

    # 策略3: 正则提取最外层JSON对象
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    json_matches = re.findall(json_pattern, text)
    for match_str in reversed(json_matches):
        try:
            data = json.loads(match_str)
            if isinstance(data, dict) and "terms" in data:
                terms = data["terms"]
                if isinstance(terms, list):
                    return [t for t in terms if isinstance(t, dict) and "term" in t]
        except (json.JSONDecodeError, TypeError):
            continue

    # 策略4: 逐条匹配 term 模式
    term_pattern = r'\{\s*"term"\s*:\s*"[^"]+"\s*,\s*"type"\s*:\s*"[^"]+"\s*\}'
    term_matches = re.findall(term_pattern, text)
    if term_matches:
        parsed_terms = []
        for tm in term_matches:
            try:
                parsed_terms.append(json.loads(tm))
            except json.JSONDecodeError:
                continue
        if parsed_terms:
            return parsed_terms

    app_logger.warning(f"无法从提取结果中解析医疗术语JSON，原文长度: {len(text)}")
    return []


def _parse_diagnosis_json(raw_text: str) -> Dict[str, Any]:
    """解析多模态诊断 LLM 返回的结构化 JSON"""
    if not raw_text:
        return {}

    text = raw_text.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从代码块提取
    for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except (json.JSONDecodeError, TypeError):
                continue

    # 尝试提取最外层 JSON
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    for match_str in reversed(re.findall(json_pattern, text)):
        try:
            return json.loads(match_str)
        except (json.JSONDecodeError, TypeError):
            continue

    return {}


@retry(max_attempts=2, delay=1.0, backoff=2.0, exceptions=(Exception,))
def _call_qwen_vl(image_base64: str, prompt: str) -> str:
    """
    调用Qwen-VL进行图片分析（带重试机制）
    """
    import dashscope
    from dashscope import MultiModalConversation

    dashscope.api_key = settings.QWEN_API_KEY

    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"data:image/jpeg;base64,{image_base64}"},
                {"text": prompt}
            ]
        }
    ]

    start_time = time.time()
    try:
        response = MultiModalConversation.call(
            model="qwen-vl-max",
            messages=messages,
            timeout=30
        )

        latency = time.time() - start_time
        app_logger.info(f"Qwen-VL调用完成，耗时: {latency:.2f}s")

        if response.status_code != 200:
            error_msg = getattr(response, 'message', f"HTTP {response.status_code}")
            raise LLMServiceException(
                f"图片分析失败: {error_msg}",
                error_code=ErrorCode.LLM_SERVICE_ERROR,
                details={"status_code": response.status_code, "latency": latency}
            )

        if (not response.output or
            not hasattr(response.output, 'choices') or
            not response.output.choices or
            len(response.output.choices) == 0 or
            not response.output.choices[0].message or
            not response.output.choices[0].message.content):
            raise LLMServiceException(
                "Qwen-VL返回内容为空",
                error_code=ErrorCode.LLM_SERVICE_ERROR,
                details={"latency": latency}
            )

        return response.output.choices[0].message.content

    except LLMServiceException:
        raise
    except Exception as e:
        latency = time.time() - start_time
        raise LLMServiceException(
            f"Qwen-VL调用异常: {str(e)}",
            error_code=ErrorCode.LLM_SERVICE_ERROR,
            details={"error_type": type(e).__name__, "latency": latency}
        )


# ==================== API 端点 ====================

@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_medical_image(
    file: UploadFile = File(...),
    prompt: str = ImagePrompts.IMAGE_ANALYZE_DEFAULT
):
    """
    分析医疗图片，提取医疗术语

    功能：
    - 文件格式和大小验证
    - 使用Qwen-VL多模态模型进行图片理解
    - 结构化医疗术语提取（多策略JSON解析）
    - 重试机制保障可靠性
    """
    try:
        image_content = await file.read()

        content_type = file.content_type or "application/octet-stream"
        is_valid, error_msg = validate_image_file(
            content_type=content_type,
            file_size=len(image_content),
            max_size=5 * 1024 * 1024
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # 使用Qwen-VL进行图片分析
        analysis_text = _call_qwen_vl(image_base64, prompt)

        # 使用LLM进一步提取结构化医疗术语
        extraction_prompt = KnowledgePrompts.format_image_terms_classify_prompt(analysis_text)

        from app.services.llm_service import llm_service
        extraction_result = llm_service.generate(
            prompt=extraction_prompt,
            temperature=0.1
        )

        medical_terms = _parse_medical_terms_json(extraction_result)

        if medical_terms:
            app_logger.info(f"成功提取 {len(medical_terms)} 个医疗术语")
        else:
            app_logger.warning("未能从分析结果中提取到结构化医疗术语，返回原始文本")

        return ImageAnalysisResponse(
            medical_terms=medical_terms,
            extracted_text=analysis_text,
            analysis_result=extraction_result or ""
        )

    except HTTPException:
        raise
    except LLMServiceException as e:
        app_logger.error(f"图片分析LLM错误: {e}")
        raise HTTPException(status_code=502, detail="图片分析服务暂时不可用，请稍后重试")
    except Exception as e:
        app_logger.error(f"图片分析失败: {e}")
        raise HTTPException(status_code=500, detail="图片分析服务暂时不可用，请稍后重试")


@router.post("/extract-terms")
async def extract_medical_terms_from_image(
    file: UploadFile = File(...)
):
    """
    从图片中提取医疗术语并查询知识图谱
    """
    try:
        analysis_result = await analyze_medical_image(file)

        if not analysis_result.medical_terms:
            return {
                "analysis": {
                    "extracted_text": analysis_result.extracted_text,
                    "analysis_result": analysis_result.analysis_result
                },
                "graph_results": [],
                "message": "未检测到可查询的医疗术语"
            }

        from app.knowledge.graph.neo4j_client import get_neo4j_client
        from app.knowledge.graph.queries import CypherQueries

        queries = CypherQueries()
        graph_results = []
        query_errors = 0

        for term_info in analysis_result.medical_terms:
            term = term_info.get("term", "").strip()
            term_type = term_info.get("type", "")

            if not term:
                continue

            try:
                neo4j = get_neo4j_client()

                if term_type == "疾病":
                    cypher_query = queries.find_disease_by_name(term)
                    graph_data = neo4j.execute_query(cypher_query, {"name": term})
                elif term_type == "药物":
                    cypher_query = "MATCH (d:Drug {name: $name}) RETURN d LIMIT 5"
                    graph_data = neo4j.execute_query(cypher_query, {"name": term})
                elif term_type == "症状":
                    cypher_query = "MATCH (s:Symptom {name: $name}) RETURN s LIMIT 5"
                    graph_data = neo4j.execute_query(cypher_query, {"name": term})
                elif term_type == "检查":
                    cypher_query = "MATCH (e:Examination {name: $name}) RETURN e LIMIT 5"
                    graph_data = neo4j.execute_query(cypher_query, {"name": term})
                else:
                    cypher_query = """
                    MATCH (n) WHERE n.name CONTAINS $name
                    RETURN n, labels(n) as nodeType
                    LIMIT 5
                    """
                    graph_data = neo4j.execute_query(cypher_query, {"name": term})

                if graph_data:
                    graph_results.append({
                        "term": term,
                        "type": term_type,
                        "graph_data": graph_data
                    })

            except Exception as e:
                query_errors += 1
                app_logger.warning(f"知识图谱查询失败（术语: {term}, 类型: {term_type}）: {e}")
                continue

        if query_errors > 0:
            app_logger.info(f"知识图谱查询完成: {len(graph_results)} 成功, {query_errors} 失败")

        return {
            "analysis": {
                "extracted_text": analysis_result.extracted_text,
                "analysis_result": analysis_result.analysis_result,
                "total_terms": len(analysis_result.medical_terms)
            },
            "graph_results": graph_results,
            "matched_count": len(graph_results)
        }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"提取医疗术语失败: {e}")
        raise HTTPException(status_code=500, detail="提取医疗术语失败，请稍后重试")


@router.post("/diagnose", response_model=MultimodalDiagnosisResponse)
async def diagnose_from_image(
    file: UploadFile = File(...),
    patient_context: str = ""
):
    """
    多模态诊断 - 从医疗图片生成结构化诊断报告

    功能：
    - 自动分类图片类型（化验单、处方、皮肤病灶、X光片等）
    - 结构化提取关键发现
    - 生成诊断摘要和建议
    - 风险评估
    - 关联知识图谱查询

    Args:
        file: 上传的医疗图片
        patient_context: 患者背景信息（可选）
    """
    try:
        image_content = await file.read()

        content_type = file.content_type or "application/octet-stream"
        is_valid, error_msg = validate_image_file(
            content_type=content_type,
            file_size=len(image_content),
            max_size=5 * 1024 * 1024
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # 构建多模态诊断 Prompt
        diagnosis_prompt = ImagePrompts.format_diagnosis_report_prompt(patient_context)

        # 调用 Qwen-VL 进行诊断
        raw_result = _call_qwen_vl(image_base64, diagnosis_prompt)
        parsed = _parse_diagnosis_json(raw_result)

        # 构建响应
        response = MultimodalDiagnosisResponse(
            image_type=parsed.get("image_type", "other"),
            image_type_confidence=float(parsed.get("image_type_confidence", 0.0)),
            findings=parsed.get("findings", []),
            summary=parsed.get("summary", raw_result[:500] if raw_result else ""),
            recommendations=parsed.get("recommendations", []),
            risk_level=parsed.get("risk_level", "low"),
            kg_references=[],
        )

        # 知识图谱关联查询
        try:
            from app.knowledge.graph.neo4j_client import get_neo4j_client
            neo4j = get_neo4j_client()

            kg_refs = []
            for finding in response.findings:
                item_name = finding.get("item", "")
                if not item_name:
                    continue

                # 根据图片类型选择查询策略
                if response.image_type == "lab_report":
                    kg_query = """
                    MATCH (n) WHERE n.name CONTAINS $name
                    RETURN n.name as name, labels(n) as type LIMIT 3
                    """
                else:
                    kg_query = """
                    MATCH (d:Disease)-[:HAS_SYMPTOM|TREATED_BY|REQUIRES_EXAM]->(r)
                    WHERE d.name CONTAINS $name OR r.name CONTAINS $name
                    RETURN d.name as disease, type(r) as rel_type, r.name as related
                    LIMIT 5
                    """

                try:
                    results = neo4j.execute_query(kg_query, {"name": item_name})
                    if results:
                        kg_refs.append({
                            "finding": item_name,
                            "kg_data": results[:5]
                        })
                except Exception:
                    pass

            response.kg_references = kg_refs
        except Exception as kg_err:
            app_logger.warning(f"诊断知识图谱关联查询失败（不影响诊断结果）: {kg_err}")

        app_logger.info(
            f"多模态诊断完成: type={response.image_type}, "
            f"findings={len(response.findings)}, risk={response.risk_level}"
        )

        return response

    except HTTPException:
        raise
    except LLMServiceException as e:
        app_logger.error(f"多模态诊断LLM错误: {e}")
        raise HTTPException(status_code=502, detail="多模态诊断服务暂时不可用，请稍后重试")
    except Exception as e:
        app_logger.error(f"多模态诊断失败: {e}")
        raise HTTPException(status_code=500, detail="多模态诊断服务暂时不可用，请稍后重试")
