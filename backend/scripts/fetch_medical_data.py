"""从公开数据集获取医疗知识库数据"""
import requests
import json
import os
from pathlib import Path
from app.utils.logger import app_logger


def fetch_icd10_data():
    """从公开源获取ICD-10疾病编码数据"""
    # 使用简化的ICD-10数据（实际可以从WHO或公开API获取）
    icd10_data = [
        {
            "code": "I10",
            "name": "高血压",
            "description": "原发性高血压",
            "category": "循环系统疾病"
        },
        {
            "code": "E11",
            "name": "2型糖尿病",
            "description": "非胰岛素依赖型糖尿病",
            "category": "内分泌、营养和代谢疾病"
        },
        {
            "code": "B16",
            "name": "急性乙型肝炎",
            "description": "乙型病毒性肝炎",
            "category": "某些传染病和寄生虫病"
        },
        {
            "code": "J11",
            "name": "流行性感冒",
            "description": "流感病毒感染",
            "category": "呼吸系统疾病"
        },
        {
            "code": "F48.0",
            "name": "神经衰弱",
            "description": "神经症性障碍",
            "category": "精神和行为障碍"
        },
        {
            "code": "G90",
            "name": "植物神经功能紊乱",
            "description": "自主神经系统疾患",
            "category": "神经系统疾病"
        },
        {
            "code": "N18",
            "name": "慢性肾脏病",
            "description": "肾功能衰竭",
            "category": "泌尿生殖系统疾病"
        },
        {
            "code": "J45",
            "name": "支气管哮喘",
            "description": "哮喘",
            "category": "呼吸系统疾病"
        },
        {
            "code": "J18",
            "name": "肺炎",
            "description": "未特指的病原体引起的肺炎",
            "category": "呼吸系统疾病"
        },
        {
            "code": "K74",
            "name": "肝纤维化和肝硬化",
            "description": "肝硬化",
            "category": "消化系统疾病"
        },
    ]
    
    return icd10_data


def fetch_drug_data():
    """获取药物数据（可以从国家药监局或公开API获取）"""
    # 示例药物数据
    drug_data = [
        {
            "name": "硝苯地平",
            "generic_name": "Nifedipine",
            "category": "钙通道阻滞剂",
            "indication": "高血压、心绞痛",
            "dosage": "10-20mg, 每日2-3次"
        },
        {
            "name": "二甲双胍",
            "generic_name": "Metformin",
            "category": "双胍类",
            "indication": "2型糖尿病",
            "dosage": "500-2000mg, 每日2-3次"
        },
        {
            "name": "恩替卡韦",
            "generic_name": "Entecavir",
            "category": "抗病毒药",
            "indication": "慢性乙型肝炎",
            "dosage": "0.5mg, 每日1次"
        },
    ]
    
    return drug_data


def fetch_medical_guidelines():
    """获取医疗指南文档（可以从公开资源下载）"""
    # 这里可以添加从公开网站下载医疗指南的逻辑
    # 例如：从PubMed、中国知网、或医疗指南网站下载PDF
    
    guidelines = [
        {
            "title": "中国高血压防治指南2023",
            "source": "中华医学会心血管病学分会",
            "url": "https://example.com/guidelines/hypertension2023.pdf"
        },
        {
            "title": "中国2型糖尿病防治指南2020",
            "source": "中华医学会糖尿病学分会",
            "url": "https://example.com/guidelines/diabetes2020.pdf"
        },
    ]
    
    return guidelines


def download_medical_documents():
    """下载医疗文档到本地"""
    data_dir = Path("./data/documents/guidelines")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    guidelines = fetch_medical_guidelines()
    
    for guideline in guidelines:
        # 这里可以添加实际的下载逻辑
        # 由于是示例，我们创建占位文件
        file_path = data_dir / f"{guideline['title']}.txt"
        if not file_path.exists():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"标题: {guideline['title']}\n")
                f.write(f"来源: {guideline['source']}\n")
                f.write(f"URL: {guideline['url']}\n\n")
                f.write("（实际内容需要从源网站下载）\n")
            app_logger.info(f"创建指南文件: {file_path}")


def fetch_from_pubmed(keywords: str, max_results: int = 10):
    """从PubMed获取医学文献（需要API key）"""
    # PubMed API示例（需要注册获取API key）
    # base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    # 这里仅提供框架，实际使用时需要配置API key
    
    app_logger.info(f"从PubMed搜索: {keywords} (需要配置API key)")
    return []


def save_medical_data_to_json():
    """保存医疗数据到JSON文件"""
    data_dir = Path("./data/knowledge_graph")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存ICD-10数据
    icd10_data = fetch_icd10_data()
    with open(data_dir / "icd10_diseases.json", "w", encoding="utf-8") as f:
        json.dump(icd10_data, f, ensure_ascii=False, indent=2)
    
    # 保存药物数据
    drug_data = fetch_drug_data()
    with open(data_dir / "drugs.json", "w", encoding="utf-8") as f:
        json.dump(drug_data, f, ensure_ascii=False, indent=2)
    
    app_logger.info("医疗数据已保存到JSON文件")


if __name__ == "__main__":
    app_logger.info("开始获取医疗知识库数据...")
    
    # 保存结构化数据
    save_medical_data_to_json()
    
    # 下载文档
    download_medical_documents()
    
    app_logger.info("医疗知识库数据获取完成")

