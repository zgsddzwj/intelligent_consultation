"""嵌入模型"""
from typing import List
import dashscope
from dashscope import TextEmbedding
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()
dashscope.api_key = settings.QWEN_API_KEY


class Embedder:
    """文本嵌入器"""
    
    def __init__(self):
        self.model = settings.QWEN_EMBEDDING_MODEL
        self.dimension = 1024  # Qwen embedding维度
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本转换为向量"""
        try:
            # 使用dashscope 1.17.0+ TextEmbedding API
            result = TextEmbedding.call(
                model=self.model,
                input=texts
            )
            
            if result.status_code == 200:
                if hasattr(result, 'output') and result.output:
                    if isinstance(result.output, dict) and 'embeddings' in result.output:
                        embeddings = [item['embedding'] for item in result.output['embeddings']]
                    elif isinstance(result.output, list):
                        embeddings = [item['embedding'] for item in result.output]
                    else:
                        app_logger.error(f"嵌入结果格式异常: {type(result.output)}")
                        raise Exception("嵌入结果格式异常")
                    return embeddings
                else:
                    app_logger.error(f"嵌入结果为空")
                    raise Exception("嵌入结果为空")
            else:
                error_msg = getattr(result, 'message', f"状态码: {result.status_code}")
                app_logger.error(f"嵌入失败: {error_msg}")
                raise Exception(f"嵌入失败: {error_msg}")
        except Exception as e:
            app_logger.error(f"嵌入过程出错: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询文本"""
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []

