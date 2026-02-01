"""知识库API"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.knowledge.rag.hybrid_search import HybridSearch
from app.knowledge.rag.document_processor import DocumentProcessor
from app.knowledge.rag.embedder import Embedder
from app.services.milvus_service import get_milvus_service
from app.services.object_storage import object_storage_service
from app.models.knowledge import KnowledgeDocument
from app.config import get_settings
from app.utils.logger import app_logger
import os
import tempfile
from pathlib import Path
from io import BytesIO

router = APIRouter()
hybrid_search = HybridSearch()
document_processor = DocumentProcessor()
embedder = Embedder()
settings = get_settings()


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: List[Dict[str, Any]]
    count: int


class GraphQueryRequest(BaseModel):
    """知识图谱查询请求"""
    operation: str
    parameters: Dict[str, Any]


class GraphVisualizationRequest(BaseModel):
    """知识图谱可视化请求"""
    department: Optional[str] = None
    disease: Optional[str] = None
    depth: int = 2  # 查询深度


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    source: str = "unknown",
    db: Session = Depends(get_db)
):
    """上传文档（存储到对象存储）"""
    try:
        # 1. 验证文件大小
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制: {file_size} > {settings.MAX_UPLOAD_SIZE}"
            )
        
        # 2. 上传到对象存储
        content_type = file.content_type or "application/octet-stream"
        upload_result = object_storage_service.upload_document(
            file_data=file_content,
            filename=file.filename,
            content_type=content_type
        )
        
        object_key = upload_result["object_key"]
        storage_type = upload_result["storage_type"]
        storage_bucket = upload_result.get("bucket", "")
        
        # 3. 处理文档（临时下载到本地处理）
        temp_file_path = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            # 处理文档
            chunks = document_processor.process_document(temp_file_path, source=source)
            
        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
        if not chunks:
            # 如果处理失败，删除已上传的文件
            object_storage_service.delete_document(object_key)
            raise HTTPException(status_code=400, detail="文档处理失败，无法提取内容")
        
        # 4. 向量化并存储
        texts = [chunk["text"] for chunk in chunks]
        vectors = embedder.embed(texts)
        
        # 5. 创建文档记录
        doc = KnowledgeDocument(
            title=file.filename,
            source=source,
            file_path=None,  # 不再使用本地路径
            object_storage_key=object_key,
            storage_type=storage_type,
            storage_bucket=storage_bucket,
            file_size=file_size,
            file_type=os.path.splitext(file.filename)[1],
            content="\n\n".join(texts),
            is_indexed="1"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # 6. 插入向量数据库
        document_ids = [doc.id] * len(chunks)
        sources = [chunk["source"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        milvus = get_milvus_service()
        vector_ids = milvus.insert(
            vectors=vectors,
            texts=texts,
            document_ids=document_ids,
            sources=sources,
            metadatas=metadatas
        )
        
        # 7. 更新文档的向量ID
        doc.vector_id = str(vector_ids[0]) if vector_ids else None
        db.commit()
        
        return {
            "document_id": doc.id,
            "title": doc.title,
            "chunks_count": len(chunks),
            "status": "indexed",
            "object_storage_key": object_key,
            "storage_type": storage_type,
            "file_size": file_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"上传文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    use_presigned_url: bool = False,
    expires: int = 3600,
    db: Session = Depends(get_db)
):
    """下载文档"""
    try:
        # 查询文档
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 如果使用预签名URL
        if use_presigned_url and doc.object_storage_key:
            url = object_storage_service.get_download_url(doc.object_storage_key, expires)
            return {"download_url": url, "expires_in": expires}
        
        # 直接下载
        if doc.object_storage_key:
            # 从对象存储下载
            file_data = object_storage_service.download_document(doc.object_storage_key)
        elif doc.file_path and os.path.exists(doc.file_path):
            # 向后兼容：从本地文件系统读取
            with open(doc.file_path, "rb") as f:
                file_data = f.read()
        else:
            raise HTTPException(status_code=404, detail="文档文件不存在")
        
        # 返回文件流
        return Response(
            content=file_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{doc.title}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"下载文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    delete_vectors: bool = True,
    db: Session = Depends(get_db)
):
    """删除文档"""
    try:
        # 查询文档
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 1. 删除对象存储中的文件
        if doc.object_storage_key:
            try:
                object_storage_service.delete_document(doc.object_storage_key)
            except Exception as e:
                app_logger.warning(f"删除对象存储文件失败: {e}")
        
        # 2. 删除本地文件（向后兼容）
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.unlink(doc.file_path)
            except Exception as e:
                app_logger.warning(f"删除本地文件失败: {e}")
        
        # 3. 删除Milvus中的向量（可选）
        if delete_vectors:
            try:
                milvus = get_milvus_service()
                if milvus._connected and milvus._collection:
                    milvus.delete_by_document_id(doc.id)
                    app_logger.info(f"已删除文档 {doc.id} 在 Milvus 中的向量")
                else:
                    app_logger.debug(f"Milvus 未连接，跳过向量删除: document_id={doc.id}")
            except Exception as e:
                app_logger.warning(f"删除向量失败（文档仍会从库中删除）: {e}")
        
        # 4. 删除数据库记录
        db.delete(doc)
        db.commit()
        
        return {
            "document_id": document_id,
            "status": "deleted",
            "message": "文档已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"删除文档失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """搜索知识库"""
    try:
        results = hybrid_search.hybrid_search(request.query, top_k=request.top_k)
        
        return SearchResponse(
            query=request.query,
            results=results,
            count=len(results)
        )
    except Exception as e:
        app_logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/query")
async def query_knowledge_graph(request: GraphQueryRequest):
    """查询知识图谱"""
    try:
        from app.knowledge.graph.neo4j_client import get_neo4j_client
        from app.knowledge.graph.queries import CypherQueries
        
        queries = CypherQueries()
        
        if request.operation == "get_disease_info":
            disease_name = request.parameters.get("disease_name")
            query = queries.find_disease_by_name(disease_name)
            neo4j = get_neo4j_client()
            result = neo4j.execute_query(query, {"name": disease_name})
            return {"operation": request.operation, "result": result}
        
        elif request.operation == "get_drug_info":
            drug_name = request.parameters.get("drug_name")
            query = "MATCH (d:Drug {name: $drug_name}) RETURN d"
            neo4j = get_neo4j_client()
            result = neo4j.execute_query(query, {"drug_name": drug_name})
            return {"operation": request.operation, "result": result}
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {request.operation}")
            
    except Exception as e:
        app_logger.error(f"知识图谱查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/visualization")
async def get_graph_visualization(request: GraphVisualizationRequest):
    """获取知识图谱可视化数据"""
    try:
        from app.knowledge.graph.neo4j_client import get_neo4j_client
        from app.knowledge.graph.queries import CypherQueries
        
        queries = CypherQueries()
        nodes = []
        links = []
        node_ids = set()
        link_ids = set()
        
        # 构建Cypher查询
        if request.department:
            # 按科室查询
            query = queries.get_department_graph(request.department, request.depth)
            neo4j = get_neo4j_client()
            result = neo4j.execute_query(query, {"dept_name": request.department})
        elif request.disease:
            # 按疾病查询
            query = f"""
            MATCH (d:Disease {{name: $disease}})
            OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
            OPTIONAL MATCH (d)-[:TREATED_BY]->(drug:Drug)
            OPTIONAL MATCH (d)-[:REQUIRES_EXAM]->(exam:Examination)
            OPTIONAL MATCH (s)-[:BELONGS_TO]->(dept:Department)
            WITH d, s, drug, exam, dept
            LIMIT 100
            RETURN d, s, drug, exam, dept
            """
            neo4j = get_neo4j_client()
            result = neo4j.execute_query(query, {"disease": request.disease})
        else:
            # 查询所有科室及其关联
            query = queries.get_all_graph_data(200)
            neo4j = get_neo4j_client()
            result = neo4j.execute_query(query, {})
        
        # 转换为可视化格式
        for record in result:
            # 处理节点和关系
            dept = record.get('dept')
            symptom = record.get('s')
            disease = record.get('d')
            drug = record.get('drug')
            exam = record.get('exam')
            
            # 添加科室节点
            if dept and dept.get('name'):
                node_id = f"dept_{dept['name']}"
                if node_id not in node_ids:
                    node_ids.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "label": dept['name'],
                        "type": "Department",
                        "properties": dict(dept)
                    })
            
            # 添加症状节点
            if symptom and symptom.get('name'):
                node_id = f"symptom_{symptom['name']}"
                if node_id not in node_ids:
                    node_ids.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "label": symptom['name'],
                        "type": "Symptom",
                        "properties": dict(symptom)
                    })
                
                # 添加症状-科室关系
                if dept and dept.get('name'):
                    link_id = f"{node_id}_belongs_to_dept_{dept['name']}"
                    if link_id not in link_ids:
                        link_ids.add(link_id)
                        links.append({
                            "source": node_id,
                            "target": f"dept_{dept['name']}",
                            "label": "所属科室"
                        })
            
            # 添加疾病节点
            if disease and disease.get('name'):
                node_id = f"disease_{disease['name']}"
                if node_id not in node_ids:
                    node_ids.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "label": disease['name'],
                        "type": "Disease",
                        "properties": dict(disease)
                    })
                
                # 添加疾病-症状关系
                if symptom and symptom.get('name'):
                    link_id = f"{node_id}_has_symptom_{symptom['name']}"
                    if link_id not in link_ids:
                        link_ids.add(link_id)
                        links.append({
                            "source": node_id,
                            "target": f"symptom_{symptom['name']}",
                            "label": "有症状"
                        })
            
            # 添加药物节点
            if drug and drug.get('name'):
                node_id = f"drug_{drug['name']}"
                if node_id not in node_ids:
                    node_ids.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "label": drug['name'],
                        "type": "Drug",
                        "properties": dict(drug)
                    })
                
                # 添加疾病-药物关系
                if disease and disease.get('name'):
                    link_id = f"disease_{disease['name']}_treated_by_{drug['name']}"
                    if link_id not in link_ids:
                        link_ids.add(link_id)
                        links.append({
                            "source": f"disease_{disease['name']}",
                            "target": node_id,
                            "label": "用药物治疗"
                        })
            
            # 添加检查节点
            if exam and exam.get('name'):
                node_id = f"exam_{exam['name']}"
                if node_id not in node_ids:
                    node_ids.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "label": exam['name'],
                        "type": "Examination",
                        "properties": dict(exam)
                    })
                
                # 添加疾病-检查关系
                if disease and disease.get('name'):
                    link_id = f"disease_{disease['name']}_requires_exam_{exam['name']}"
                    if link_id not in link_ids:
                        link_ids.add(link_id)
                        links.append({
                            "source": f"disease_{disease['name']}",
                            "target": node_id,
                            "label": "需要检查"
                        })
        
        return {
            "nodes": nodes,
            "links": links
        }
        
    except Exception as e:
        app_logger.error(f"获取图谱可视化数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/departments")
async def get_departments():
    """获取所有科室列表"""
    try:
        from app.knowledge.graph.neo4j_client import get_neo4j_client
        
        query = "MATCH (d:Department) RETURN d.name as name, d.description as description ORDER BY d.name"
        neo4j = get_neo4j_client()
        result = neo4j.execute_query(query, {})
        
        return {
            "departments": [
                {"name": r.get("name"), "description": r.get("description")}
                for r in result
            ]
        }
    except Exception as e:
        # Neo4j连接失败时，返回空列表而不是抛出异常（降级策略）
        app_logger.warning(f"获取科室列表失败（Neo4j可能未连接），返回空列表: {e}")
        return {
            "departments": []
        }
