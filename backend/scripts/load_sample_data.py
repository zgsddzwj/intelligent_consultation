"""加载示例数据"""
from app.knowledge.rag.document_processor import DocumentProcessor
from app.knowledge.rag.embedder import Embedder
from app.services.milvus_service import milvus_service
from app.utils.logger import app_logger
import os


def create_sample_documents():
    """创建示例文档"""
    sample_dir = "./data/sample"
    os.makedirs(sample_dir, exist_ok=True)
    
    # 创建示例医疗文档
    sample_docs = [
        {
            "filename": "高血压诊疗指南.txt",
            "content": """高血压诊疗指南

一、定义
高血压是指收缩压≥140mmHg和/或舒张压≥90mmHg。

二、诊断标准
1. 在未使用降压药物的情况下，非同日3次测量诊室血压，收缩压≥140mmHg和/或舒张压≥90mmHg。
2. 患者既往有高血压史，目前正在使用降压药物，血压虽然低于140/90mmHg，仍应诊断为高血压。

三、治疗原则
1. 生活方式干预：低盐饮食、适量运动、控制体重、戒烟限酒。
2. 药物治疗：根据患者情况选择合适的降压药物，如ACEI、ARB、CCB等。
3. 目标血压：一般患者<140/90mmHg，合并糖尿病或慢性肾脏病患者<130/80mmHg。

四、常用药物
1. 钙通道阻滞剂（CCB）：如硝苯地平、氨氯地平等。
2. 血管紧张素转换酶抑制剂（ACEI）：如卡托普利、依那普利等。
3. 血管紧张素II受体拮抗剂（ARB）：如氯沙坦、缬沙坦等。

五、注意事项
1. 定期监测血压。
2. 遵医嘱服药，不可自行停药。
3. 注意药物不良反应。
4. 定期复查，评估治疗效果。

来源：《中国高血压防治指南2023》
"""
        },
        {
            "filename": "糖尿病管理指南.txt",
            "content": """糖尿病管理指南

一、定义
糖尿病是一组以高血糖为特征的代谢性疾病，是由于胰岛素分泌缺陷或其生物作用受损，或两者兼有引起。

二、诊断标准
1. 空腹血糖≥7.0mmol/L。
2. 随机血糖≥11.1mmol/L。
3. 糖化血红蛋白（HbA1c）≥6.5%。

三、治疗目标
1. 血糖控制：空腹血糖4.4-7.0mmol/L，餐后2小时血糖<10.0mmol/L。
2. 糖化血红蛋白：<7.0%。
3. 血压：<130/80mmHg。
4. 血脂：LDL-C<2.6mmol/L。

四、治疗方案
1. 生活方式干预：饮食控制、运动锻炼、体重管理。
2. 药物治疗：
   - 一线药物：二甲双胍
   - 二线药物：磺脲类、DPP-4抑制剂、GLP-1受体激动剂等
   - 胰岛素治疗：适用于1型糖尿病或2型糖尿病血糖控制不佳者

五、监测指标
1. 血糖监测：每日监测空腹和餐后血糖。
2. 糖化血红蛋白：每3个月检测一次。
3. 并发症筛查：定期检查眼底、肾功能、神经病变等。

六、注意事项
1. 严格遵医嘱用药。
2. 注意低血糖反应。
3. 定期复查，调整治疗方案。
4. 预防并发症。

来源：《中国2型糖尿病防治指南2020》
"""
        }
    ]
    
    # 保存示例文档
    for doc in sample_docs:
        file_path = os.path.join(sample_dir, doc["filename"])
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc["content"])
        app_logger.info(f"创建示例文档: {file_path}")
    
    return [os.path.join(sample_dir, doc["filename"]) for doc in sample_docs]


def load_sample_data_to_vector_db():
    """将示例数据加载到向量数据库"""
    processor = DocumentProcessor()
    embedder = Embedder()
    
    # 创建示例文档
    doc_files = create_sample_documents()
    
    # 处理并索引文档
    for file_path in doc_files:
        try:
            # 处理文档
            chunks = processor.process_document(
                file_path,
                source=os.path.basename(file_path)
            )
            
            if not chunks:
                continue
            
            # 向量化
            texts = [chunk["text"] for chunk in chunks]
            vectors = embedder.embed(texts)
            
            # 插入向量数据库
            document_ids = [1] * len(chunks)  # 示例文档ID
            sources = [chunk["source"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            
            milvus_service.insert(
                vectors=vectors,
                texts=texts,
                document_ids=document_ids,
                sources=sources,
                metadatas=metadatas
            )
            
            app_logger.info(f"已索引文档: {file_path}, 块数: {len(chunks)}")
            
        except Exception as e:
            app_logger.error(f"处理文档失败: {file_path}, {e}")


if __name__ == "__main__":
    load_sample_data_to_vector_db()

