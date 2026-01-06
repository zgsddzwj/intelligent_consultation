"""加载医疗知识到知识图谱和向量数据库"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.graph.builder import KnowledgeGraphBuilder
from app.knowledge.rag.document_processor import DocumentProcessor
from app.knowledge.rag.embedder import Embedder
from app.services.milvus_service import get_milvus_service
from app.services.object_storage import object_storage_service
from app.utils.logger import app_logger


def load_icd10_to_graph():
    """将ICD-10数据加载到知识图谱"""
    builder = KnowledgeGraphBuilder()
    
    data_file = Path("./data/knowledge_graph/icd10_diseases.json")
    if not data_file.exists():
        app_logger.warning(f"ICD-10数据文件不存在: {data_file}")
        return
    
    with open(data_file, "r", encoding="utf-8") as f:
        diseases = json.load(f)
    
    for disease in diseases:
        try:
            builder.create_entity("Disease", disease["name"], {
                "icd10": disease["code"],
                "description": disease.get("description", ""),
                "category": disease.get("category", "")
            })
            app_logger.info(f"已加载疾病: {disease['name']} ({disease['code']})")
        except Exception as e:
            app_logger.warning(f"疾病 {disease['name']} 可能已存在: {e}")


def load_drugs_to_graph():
    """将药物数据加载到知识图谱"""
    builder = KnowledgeGraphBuilder()
    
    data_file = Path("./data/knowledge_graph/drugs.json")
    if not data_file.exists():
        app_logger.warning(f"药物数据文件不存在: {data_file}")
        return
    
    with open(data_file, "r", encoding="utf-8") as f:
        drugs = json.load(f)
    
    for drug in drugs:
        try:
            builder.create_entity("Drug", drug["name"], {
                "generic_name": drug.get("generic_name", ""),
                "category": drug.get("category", ""),
                "indication": drug.get("indication", ""),
                "dosage": drug.get("dosage", "")
            })
            app_logger.info(f"已加载药物: {drug['name']}")
        except Exception as e:
            app_logger.warning(f"药物 {drug['name']} 可能已存在: {e}")


def upload_local_documents_to_storage(docs_dir: Path = None):
    """将本地文档上传到对象存储"""
    if docs_dir is None:
        docs_dir = Path("./data/documents/guidelines")
    
    if not docs_dir.exists():
        app_logger.warning(f"文档目录不存在: {docs_dir}")
        return []
    
    uploaded_files = []
    
    # 支持多种文件格式
    file_patterns = ["*.txt", "*.pdf", "*.docx", "*.doc"]
    
    for pattern in file_patterns:
        for file_path in docs_dir.glob(pattern):
            try:
                # 读取文件
                with open(file_path, "rb") as f:
                    file_data = f.read()
                
                # 上传到对象存储
                upload_result = object_storage_service.upload_document(
                    file_data=file_data,
                    filename=file_path.name
                )
                
                uploaded_files.append({
                    "local_path": str(file_path),
                    "object_key": upload_result["object_key"],
                    "storage_type": upload_result["storage_type"]
                })
                
                app_logger.info(f"已上传文档到对象存储: {file_path.name} -> {upload_result['object_key']}")
                
            except Exception as e:
                app_logger.error(f"上传文档失败: {file_path}, {e}")
    
    return uploaded_files


def load_documents_to_vector_db(use_object_storage: bool = True):
    """
    将医疗文档加载到向量数据库
    
    Args:
        use_object_storage: 是否使用对象存储（True：从对象存储读取，False：从本地读取）
    """
    processor = DocumentProcessor()
    embedder = Embedder()
    
    if use_object_storage:
        # 从对象存储加载
        # 列出所有文档
        files = object_storage_service.client.list_files(prefix="documents/")
        
        for file_info in files:
            object_key = file_info["key"]
            try:
                # 从对象存储处理文档
                chunks = processor.process_document_from_storage(
                    object_key=object_key,
                    source=Path(object_key).name
                )
                
                if not chunks:
                    continue
                
                # 向量化
                texts = [chunk["text"] for chunk in chunks]
                vectors = embedder.embed(texts)
                
                # 插入向量数据库
                document_ids = [hash(object_key) % 1000000] * len(chunks)
                sources = [chunk["source"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                
                milvus = get_milvus_service()
                milvus.insert(
                    vectors=vectors,
                    texts=texts,
                    document_ids=document_ids,
                    sources=sources,
                    metadatas=metadatas
                )
                
                app_logger.info(f"已加载文档到向量数据库: {object_key}, 块数: {len(chunks)}")
                
            except Exception as e:
                app_logger.error(f"处理文档失败: {object_key}, {e}")
    else:
        # 从本地文件系统加载（向后兼容）
        docs_dir = Path("./data/documents/guidelines")
        if not docs_dir.exists():
            app_logger.warning(f"文档目录不存在: {docs_dir}")
            return
        
        for file_path in docs_dir.glob("*.txt"):
            try:
                # 处理文档
                chunks = processor.process_document(
                    str(file_path),
                    source=file_path.name
                )
                
                if not chunks:
                    continue
                
                # 向量化
                texts = [chunk["text"] for chunk in chunks]
                vectors = embedder.embed(texts)
                
                # 插入向量数据库
                document_ids = [hash(file_path.name) % 1000000] * len(chunks)
                sources = [chunk["source"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                
                milvus = get_milvus_service()
                milvus.insert(
                    vectors=vectors,
                    texts=texts,
                    document_ids=document_ids,
                    sources=sources,
                    metadatas=metadatas
                )
                
                app_logger.info(f"已加载文档到向量数据库: {file_path.name}, 块数: {len(chunks)}")
                
            except Exception as e:
                app_logger.error(f"处理文档失败: {file_path}, {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="加载医疗知识")
    parser.add_argument("--upload-to-storage", action="store_true", 
                       help="将本地文档上传到对象存储")
    parser.add_argument("--use-storage", action="store_true", 
                       help="从对象存储加载文档（而不是本地文件系统）")
    args = parser.parse_args()
    
    app_logger.info("开始加载医疗知识...")
    
    # 加载到知识图谱
    load_icd10_to_graph()
    load_drugs_to_graph()
    
    # 如果需要，先上传本地文档到对象存储
    if args.upload_to_storage:
        app_logger.info("上传本地文档到对象存储...")
        uploaded = upload_local_documents_to_storage()
        app_logger.info(f"已上传 {len(uploaded)} 个文档到对象存储")
    
    # 加载到向量数据库
    load_documents_to_vector_db(use_object_storage=args.use_storage)
    
    app_logger.info("医疗知识加载完成")

