"""图片分析API"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger
import base64
import dashscope
from dashscope import MultiModalConversation
from app.config import get_settings

settings = get_settings()
dashscope.api_key = settings.QWEN_API_KEY

router = APIRouter()


class ImageAnalysisRequest(BaseModel):
    """图片分析请求"""
    image_base64: str
    prompt: Optional[str] = "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并提取出来。"


class ImageAnalysisResponse(BaseModel):
    """图片分析响应"""
    medical_terms: List[Dict[str, str]]  # [{"term": "高血压", "type": "疾病"}, ...]
    extracted_text: str
    analysis_result: str


@router.post("/analyze")
async def analyze_medical_image(
    file: UploadFile = File(...),
    prompt: str = "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并提取出来。"
):
    """分析医疗图片，提取医疗术语"""
    try:
        # 读取图片
        image_content = await file.read()
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # 使用Qwen-VL进行图片分析
        prompt = "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并提取出来。"
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
        
        response = MultiModalConversation.call(
            model="qwen-vl-max",
            messages=messages
        )
        
        if response.status_code != 200:
            raise Exception(f"图片分析失败: {response.message}")
        
        analysis_text = response.output.choices[0].message.content
        
        # 提取医疗术语（使用LLM进一步处理）
        extraction_prompt = f"""
        请从以下文本中提取医疗相关术语，并按类型分类：
        
        {analysis_text}
        
        请以JSON格式返回，格式如下：
        {{
            "terms": [
                {{"term": "术语名称", "type": "疾病|症状|药物|检查|科室"}},
                ...
            ]
        }}
        """
        
        from app.services.llm_service import llm_service
        extraction_result = llm_service.generate(
            prompt=extraction_prompt,
            temperature=0.3
        )
        
        # 解析提取结果（简化处理）
        medical_terms = []
        # 这里可以添加更复杂的解析逻辑
        
        return ImageAnalysisResponse(
            medical_terms=medical_terms,
            extracted_text=analysis_text,
            analysis_result=extraction_result
        )
        
    except Exception as e:
        app_logger.error(f"图片分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-terms")
async def extract_medical_terms_from_image(
    file: UploadFile = File(...)
):
    """从图片中提取医疗术语并查询知识图谱"""
    try:
        # 分析图片
        analysis_result = await analyze_medical_image(file)
        
        # 查询知识图谱
        from app.knowledge.graph.neo4j_client import neo4j_client
        from app.knowledge.graph.queries import CypherQueries
        
        queries = CypherQueries()
        graph_results = []
        
        for term_info in analysis_result.medical_terms:
            term = term_info.get("term")
            term_type = term_info.get("type")
            
            if term_type == "疾病":
                result = queries.find_disease_by_name(term)
                graph_data = neo4j_client.execute_query(result, {"name": term})
                if graph_data:
                    graph_results.append({
                        "term": term,
                        "type": term_type,
                        "graph_data": graph_data
                    })
        
        return {
            "analysis": analysis_result,
            "graph_results": graph_results
        }
        
    except Exception as e:
        app_logger.error(f"提取医疗术语失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

