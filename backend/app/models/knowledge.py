"""知识库模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database.base import Base


class KnowledgeDocument(Base):
    """知识文档表"""
    __tablename__ = "knowledge_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    source = Column(String(255), nullable=False)  # 文档来源
    file_path = Column(String(500), nullable=True)  # 文件路径
    file_type = Column(String(50), nullable=True)  # 文件类型（pdf, docx等）
    content = Column(Text, nullable=True)  # 文档内容
    metadata = Column(JSON, default=dict)  # 元数据（页码、章节等）
    vector_id = Column(String(100), nullable=True, index=True)  # Milvus向量ID
    is_indexed = Column(String(1), default="0", nullable=False)  # 是否已索引
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

