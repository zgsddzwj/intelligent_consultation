"""图片分析API - 增强版（输入验证、重试机制、JSON解析优化）"""
import re
import json
import base64
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set
from app.utils.logger import app_logger
from app.infrastructure.retry import retry
from app.common.exceptions import ValidationException, LLMServiceException, ErrorCode
from app.config import get_settings

settings = get_settings()

# 支持的图片格式及对应的MIME类型
ALLOWED_IMAGE_TYPES: Set[str] = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"
}
# 对应的文件扩展名
ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# 最大文件大小：10MB
MAX_IMAGE_SIZE: int = 10 * 1024 * 1024

router = APIRouter()


class ImageAnalysisRequest(BaseModel):
    """图片分析请求"""
    image_base64: str
    prompt: Optional[str] = Field(
        default="请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并提取出来。",
        description="分析提示词"
    )


class ImageAnalysisResponse(BaseModel):
    """图片分析响应"""
    medical_terms: List[Dict[str, str]]  # [{"term": "高血压", "type": "疾病"}, ...]
    extracted_text: str
    analysis_result: str


def _validate_image_file(file: UploadFile) -> None:
    """
    验证上传的图片文件
    
    Args:
        file: 上传的文件对象
        
    Raises:
        ValidationException: 文件验证失败时抛出
    """
    # 检查文件名和扩展名
    if not file.filename:
        raise ValidationException(
            "文件名不能为空",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "filename"}
        )
    
    # 检查文件扩展名
    from pathlib import Path
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(
            f"不支持的图片格式: {ext}，支持格式: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={
                "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
                "provided_extension": ext
            }
        )
    
    # 检查MIME类型
    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        # MIME类型检查作为警告而非硬性拒绝（某些浏览器可能发送错误的MIME类型）
        app_logger.warning(f"可疑的MIME类型: {content_type}, 文件名: {file.filename}")


def _parse_medical_terms_json(extraction_result: str) -> List[Dict[str, str]]:
    """
    从LLM提取结果中解析医疗术语JSON
    
    使用多种策略尝试解析：
    1. 标准JSON解析
    2. Markdown代码块提取后解析
    3. 正则表达式提取JSON对象
    4. 逐行解析 fallback
    
    Args:
        extraction_result: LLM返回的原始文本
        
    Returns:
        解析后的术语列表
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
    for match_str in reversed(json_matches):  # 从最外层的匹配开始
        try:
            data = json.loads(match_str)
            if isinstance(data, dict) and "terms" in data:
                terms = data["terms"]
                if isinstance(terms, list):
                    return [t for t in terms if isinstance(t, dict) and "term" in t]
        except (json.JSONDecodeError, TypeError):
            continue
    
    # 策略4: 尝试查找任何包含term字段的字典模式
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


@retry(max_attempts=2, delay=1.0, backoff=2.0, exceptions=(Exception,))
def _call_qwen_vl(image_base64: str, prompt: str) -> str:
    """
    调用Qwen-VL进行图片分析（带重试机制）
    
    Args:
        image_base64: Base64编码的图片数据
        prompt: 分析提示词
        
    Returns:
        分析结果文本
        
    Raises:
        LLMServiceException: 调用失败时抛出
    """
    import dashscope
    from dashscope import MultiModalConversation
    
    dashscope.api_key = settings.QWEN_API_KEY
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "image": f"data:image/jpeg;base64,{image_base64}"
                },
                {
                    "text": prompt
                }
            ]
        }
    ]
    
    start_time = time.time()
    try:
        response = MultiModalConversation.call(
            model="qwen-vl-max",
            messages=messages,
            timeout=30  # 30秒超时
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
        
        # 安全获取响应内容
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


@router.post("/analyze")
async def analyze_medical_image(
    file: UploadFile = File(...),
    prompt: str = "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并提取出来。"
):
    """
    分析医疗图片，提取医疗术语
    
    功能增强：
    - 文件格式和大小验证
    - 使用用户自定义prompt（替代硬编码）
    - 完整的JSON解析（多策略fallback）
    - 重试机制保障可靠性
    - 结构化错误信息
    """
    consultation_id = 0
    
    try:
        # 1. 验证文件
        _validate_image_file(file)
        
        # 2. 读取并验证图片大小
        image_content = await file.read()
        file_size = len(image_content)
        
        if file_size == 0:
            raise ValidationException(
                "上传的文件为空",
                error_code=ErrorCode.VALIDATION_ERROR,
                details={"field": "file_content"}
            )
        
        if file_size > MAX_IMAGE_SIZE:
            raise ValidationException(
                f"文件大小超过限制: {file_size / (1024 * 1024):.1f}MB > {MAX_IMAGE_SIZE / (1024 * 1024):.0f}MB",
                error_code=ErrorCode.VALIDATION_ERROR,
                details={
                    "file_size": file_size,
                    "max_size": MAX_IMAGE_SIZE
                }
            )
        
        # 3. 编码为Base64
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # 4. 使用Qwen-VL进行图片分析（使用传入的prompt参数）
        analysis_text = _call_qwen_vl(image_base64, prompt)
        
        if not analysis_text or not analysis_text.strip():
            raise LLMServiceException(
                "图片分析结果为空",
                error_code=ErrorCode.LLM_SERVICE_ERROR
            )
        
        # 5. 使用LLM进一步处理，提取结构化医疗术语
        extraction_prompt = f"""请从以下文本中提取医疗相关术语，并按类型分类：

{analysis_text}

请以JSON格式返回，格式如下：
{{
    "terms": [
        {{"term": "术语名称", "type": "疾病|症状|药物|检查|科室"}},
        ...
    ]
}}

注意：
- 只返回JSON，不要添加其他说明文字
- type字段只能是：疾病、症状、药物、检查、科室 之一
- 如果没有识别到医疗术语，返回空数组"""

        from app.services.llm_service import llm_service
        extraction_result = llm_service.generate(
            prompt=extraction_prompt,
            temperature=0.1  # 低温度确保输出稳定
        )
        
        # 6. 使用多策略JSON解析
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
        
    except (ValidationException, LLMServiceException):
        raise
    except Exception as e:
        app_logger.error(f"图片分析失败: {e}", exc_info=True)
        # 不暴露内部错误细节给客户端
        raise HTTPException(
            status_code=500,
            detail="图片分析服务暂时不可用，请稍后重试"
        )


@router.post("/extract-terms")
async def extract_medical_terms_from_image(
    file: UploadFile = File(...)
):
    """
    从图片中提取医疗术语并查询知识图谱
    
    增强：
    - 复用analyze接口的逻辑
    - 批量查询知识图谱
    - 错误隔离（单个术语查询失败不影响其他）
    """
    try:
        # 分析图片（复用上面的完整流程）
        analysis_result = await analyze_medical_image(file)
        
        # 如果没有提取到术语，直接返回
        if not analysis_result.medical_terms:
            return {
                "analysis": {
                    "extracted_text": analysis_result.extracted_text,
                    "analysis_result": analysis_result.analysis_result
                },
                "graph_results": [],
                "message": "未检测到可查询的医疗术语"
            }
        
        # 查询知识图谱
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
                    # 通用搜索
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
                # 继续处理下一个术语
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
        
    except (ValidationException, LLMServiceException, HTTPException):
        raise
    except Exception as e:
        app_logger.error(f"提取医疗术语失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="术语提取服务暂时不可用，请稍后重试"
        )
