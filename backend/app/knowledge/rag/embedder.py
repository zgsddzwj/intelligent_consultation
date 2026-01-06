"""嵌入模型"""
from typing import List
import dashscope
try:
    from dashscope import Embeddings
except ImportError:
    # 新版本dashscope使用不同的API
    try:
        from dashscope import BatchTextEmbedding as Embeddings
    except ImportError:
        Embeddings = None
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
            if Embeddings is None:
                # 使用新API
                from dashscope import BatchTextEmbedding
                result = BatchTextEmbedding.call(
                    model=self.model,
                    input=texts
                )
            else:
                result = Embeddings.call(
                    model=self.model,
                    input=texts
                )
            
            if result.status_code == 200:
                embeddings = [item['embedding'] for item in result.output['embeddings']]
                return embeddings
            else:
                app_logger.error(f"嵌入失败: {result.message}")
                raise Exception(f"嵌入失败: {result.message}")
        except Exception as e:
            app_logger.error(f"嵌入过程出错: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询文本"""
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []

