"""知识库API"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.knowledge.rag.hybrid_search import HybridSearch
from app.knowledge.rag.document_processor import DocumentProcessor
from app.knowledge.rag.embedder import Embedder
from app.services.milvus_service import milvus_service
from app.models.knowledge import KnowledgeDocument
from app.utils.logger import app_logger
import os

router = APIRouter()
hybrid_search = HybridSearch()
document_processor = DocumentProcessor()
embedder = Embedder()


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
    """上传文档"""
    try:
        # 保存文件
        upload_dir = "./data/documents"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 处理文档
        chunks = document_processor.process_document(file_path, source=source)
        
        # 向量化并存储
        texts = [chunk["text"] for chunk in chunks]
        vectors = embedder.embed(texts)
        
        # 创建文档记录
        doc = KnowledgeDocument(
            title=file.filename,
            source=source,
            file_path=file_path,
            file_type=os.path.splitext(file.filename)[1],
            content="\n\n".join(texts),
            is_indexed="1"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # 插入向量数据库
        document_ids = [doc.id] * len(chunks)
        sources = [chunk["source"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        vector_ids = milvus_service.insert(
            vectors=vectors,
            texts=texts,
            document_ids=document_ids,
            sources=sources,
            metadatas=metadatas
        )
        
        # 更新文档的向量ID
        doc.vector_id = str(vector_ids[0]) if vector_ids else None
        db.commit()
        
        return {
            "document_id": doc.id,
            "title": doc.title,
            "chunks_count": len(chunks),
            "status": "indexed"
        }
        
    except Exception as e:
        app_logger.error(f"上传文档失败: {e}")
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
        from app.knowledge.graph.neo4j_client import neo4j_client
        from app.knowledge.graph.queries import CypherQueries
        
        queries = CypherQueries()
        
        if request.operation == "get_disease_info":
            disease_name = request.parameters.get("disease_name")
            query = queries.find_disease_by_name(disease_name)
            result = neo4j_client.execute_query(query, {"name": disease_name})
            return {"operation": request.operation, "result": result}
        
        elif request.operation == "get_drug_info":
            drug_name = request.parameters.get("drug_name")
            query = "MATCH (d:Drug {name: $drug_name}) RETURN d"
            result = neo4j_client.execute_query(query, {"drug_name": drug_name})
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
        from app.knowledge.graph.neo4j_client import neo4j_client
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
            result = neo4j_client.execute_query(query, {"dept_name": request.department})
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
            result = neo4j_client.execute_query(query, {"disease": request.disease})
        else:
            # 查询所有科室及其关联
            query = queries.get_all_graph_data(200)
            result = neo4j_client.execute_query(query, {})
        
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
        from app.knowledge.graph.neo4j_client import neo4j_client
        
        query = "MATCH (d:Department) RETURN d.name as name, d.description as description ORDER BY d.name"
        result = neo4j_client.execute_query(query, {})
        
        return {
            "departments": [
                {"name": r.get("name"), "description": r.get("description")}
                for r in result
            ]
        }
    except Exception as e:
        app_logger.error(f"获取科室列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
